#!/usr/bin/env python3
"""
Standalone MLOps Script for Sentinel
Bypasses Vertex AI Pipelines to avoid custom_model_training_cpus quota issues.
Runs locally and triggers Gemini tuning via the Vertex AI SDK directly.
"""

import json
import logging
from google.cloud import bigquery
from google.cloud import storage
import vertexai
from vertexai.preview.tuning import sft

# Configuration
PROJECT_ID = "sentinel-ai-project-482208"
LOCATION = "us-central1"  # For tuning API, us-central1 is usually required
BUCKET_NAME = "sentinel-mlops-artifacts-sentinel-ai-project-482208"
BQ_TABLE_ID = f"{PROJECT_ID}.retail_ai.gemini_tuning_dataset"
MODEL_DISPLAY_NAME = "sentinel-gemini-tuned-local"
TRAINING_DATA_FILE = "training_data_local.jsonl"

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def export_data_to_gcs():
    """
    Step 1: Export data from BigQuery to GCS in JSONL format.
    """
    logger.info("=" * 50)
    logger.info("Step 1: Exporting data from BigQuery to GCS")
    logger.info("=" * 50)
    
    bq_client = bigquery.Client(project=PROJECT_ID)
    storage_client = storage.Client(project=PROJECT_ID)
    
    logger.info(f"Querying BigQuery table: {BQ_TABLE_ID}")
    query = f"SELECT * FROM `{BQ_TABLE_ID}`"
    query_job = bq_client.query(query)
    rows = query_job.result()
    
    # Get schema for column mapping
    schema_fields = {field.name.lower(): field.name for field in rows.schema}
    logger.info(f"Schema columns: {list(schema_fields.keys())}")
    
    jsonl_data = []
    count = 0
    
    for row in rows:
        row_data = {}
        for k_lower, k_original in schema_fields.items():
            row_data[k_lower] = row[k_original]
        
        user_t = row_data.get('prompt') or row_data.get('input') or row_data.get('question')
        model_t = row_data.get('response') or row_data.get('output') or row_data.get('answer')
        
        if user_t and model_t:
            # GenerateContent format for Gemini 2.0 (NOT ChatCompletions format!)
            jsonl_data.append({
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": str(user_t)}]
                    },
                    {
                        "role": "model",
                        "parts": [{"text": str(model_t)}]
                    }
                ]
            })
            count += 1
    
    if not jsonl_data:
        raise ValueError("No valid training pairs found in BigQuery!")
    
    logger.info(f"Extracted {count} valid training pairs.")
    
    # Upload to GCS
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(TRAINING_DATA_FILE)
    blob.upload_from_string(
        "\n".join([json.dumps(r) for r in jsonl_data]),
        content_type="application/jsonl"
    )
    
    gcs_uri = f"gs://{BUCKET_NAME}/{TRAINING_DATA_FILE}"
    logger.info(f"Uploaded training data to: {gcs_uri}")
    
    return gcs_uri


def trigger_gemini_tuning(training_data_uri: str):
    """
    Step 2: Trigger Gemini fine-tuning via Vertex AI SDK.
    This uses the sft.train API which does NOT require custom_model_training_cpus quota!
    """
    logger.info("=" * 50)
    logger.info("Step 2: Triggering Gemini Fine-Tuning")
    logger.info("=" * 50)
    
    logger.info(f"Initializing Vertex AI: project={PROJECT_ID}, location={LOCATION}")
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    
    source_model = "gemini-2.0-flash-001"  # Gemini 2.0 Flash supports fine-tuning
    
    logger.info(f"Source model: {source_model}")
    logger.info(f"Training data: {training_data_uri}")
    logger.info(f"Display name: {MODEL_DISPLAY_NAME}")
    
    logger.info("Submitting tuning job... (This may take a few minutes to start)")
    
    try:
        tuning_job = sft.train(
            source_model=source_model,
            train_dataset=training_data_uri,
            epochs=5,
            tuned_model_display_name=MODEL_DISPLAY_NAME,
        )
        
        logger.info(f"✅ Tuning job submitted successfully!")
        logger.info(f"Job Resource Name: {tuning_job.resource_name}")
        logger.info(f"Job State: {tuning_job.state}")
        
        return tuning_job.resource_name
        
    except Exception as e:
        logger.error(f"Failed to submit tuning job: {e}")
        raise


def main():
    """
    Main entry point - runs the complete MLOps flow locally.
    """
    logger.info("🚀 Starting Sentinel MLOps Local Pipeline")
    logger.info(f"Project: {PROJECT_ID}")
    logger.info(f"Location: {LOCATION}")
    
    # Step 1: Export data
    training_data_uri = export_data_to_gcs()
    
    # Step 2: Trigger tuning
    job_name = trigger_gemini_tuning(training_data_uri)
    
    logger.info("=" * 50)
    logger.info("🎉 Pipeline Complete!")
    logger.info(f"Tuning Job: {job_name}")
    logger.info("Monitor progress in Vertex AI Console > Model Development > Tuning")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
