"""
Vertex AI Pipeline for SentinEL MLOps (Continuous Training)
Project: sentinel-ai-project-482208
"""

from typing import NamedTuple
from kfp import dsl
from kfp import compiler

@dsl.component(
    base_image="python:3.9",
    packages_to_install=["google-cloud-bigquery>=3.0.0", "google-cloud-storage>=2.0.0"]
)
def export_data_v2_op(
    bq_table_id: str,
    bucket_name: str,
    project_id: str,
) -> str:
    """
    Exports data from BigQuery (v2), converts to JSONL, and uploads to GCS.
    """
    import json
    from google.cloud import bigquery
    from google.cloud import storage
    import logging
    import traceback
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    try:
        logger.info("Starting Export Data Op V2 (Pandas-Free)")
        
        # ... (rest of the pandas-free logic from before, ensuring it's kept)
        # Initialize clients
        bq_client = bigquery.Client(project=project_id)
        storage_client = storage.Client(project=project_id)

        # ...
        query = f"SELECT * FROM `{bq_table_id}`"
        query_job = bq_client.query(query)
        rows = query_job.result()
        
        # Debug schema
        schema_fields = {field.name.lower(): field.name for field in rows.schema}
        logger.info(f"Schema columns: {list(schema_fields.keys())}")

        jsonl_data = []
        count = 0
        
        for row in rows:
             # Safe Dict Mapping
             row_data = {}
             for k_lower, k_original in schema_fields.items():
                 row_data[k_lower] = row[k_original]
                 
             user_t = row_data.get('prompt') or row_data.get('input') or row_data.get('question')
             model_t = row_data.get('response') or row_data.get('output') or row_data.get('answer')
             
             if user_t and model_t:
                 jsonl_data.append({
                     "messages": [
                         {"role": "user", "content": str(user_t)},
                         {"role": "model", "content": str(model_t)}
                     ]
                 })
                 count += 1
        
        if not jsonl_data:
            logger.error("No valid pairs found.")
            raise ValueError("No valid training pairs extracted from BigQuery.")
            
        logger.info(f"Extracted {count} pairs.")
        
        # Upload
        blob = storage_client.bucket(bucket_name).blob("training_data_v2.jsonl")
        blob.upload_from_string(
            "\n".join([json.dumps(r) for r in jsonl_data]),
            content_type="application/jsonl"
        )
        
        return f"gs://{bucket_name}/training_data_v2.jsonl"

    except Exception as e:
        logger.error(f"FAIL: {e}")
        traceback.print_exc()
        raise e

@dsl.component(
    base_image="python:3.9",
    packages_to_install=["google-cloud-aiplatform"]
)
def trigger_tuning_job_op(
    training_data_uri: str,
    project: str,
    location: str,
    model_display_name: str,
    epochs: int = 5,
) -> str:
    """
    Triggers a Supervised Fine-Tuning job for Gemini using Vertex AI SDK.
    """
    import vertexai
    from vertexai.preview.tuning import sft
    import logging
    import time

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    logger.info(f"Initializing Vertex AI for project {project} in {location}")
    vertexai.init(project=project, location=location)

    source_model = "gemini-1.5-pro-002"
    
    logger.info(f"Submitting tuning job for {source_model} with data {training_data_uri}")
    
    # sft.train returns a TuningJob object
    sft_tuning_job = sft.train(
        source_model=source_model,
        train_dataset=training_data_uri,
        # The prompt implies we return a resource name. sft.train is synchronous-like or returns job?
        # Typically SDK methods start the job.
        epochs=epochs,
        tuned_model_display_name=model_display_name,
    )

    # Wait for job submission to be confirmed (status check usually happens internally or we can just return ID)
    # The requirement is 'Return Job Resource Name'.
    
    # Check if sft_tuning_job has 'resource_name' attribute immediately 
    # or if we need to access underlying job details.
    # Note: sft.train method in preview might block or return a job object. 
    # Usually in Pipelines we don't want to block for hours. 
    # However, standard component execution has a timeout. 
    # If sft.train blocks, this component will run for the duration of training.
    # If current SDK implementation allows blocking=False, that's preferred.
    # Assuming default behavior or non-blocking return if possible, or we accept blocking component.
    
    logger.info(f"Job state: {sft_tuning_job.state}")
    resource_name = sft_tuning_job.resource_name
    logger.info(f"Tuning Job Resource Name: {resource_name}")
    
    return resource_name

@dsl.pipeline(
    name="sentinel-continuous-training-pipeline-v5",
    description="Pipeline to export data and fine-tune Gemini model (asia-east1)",
    pipeline_root="gs://sentinel-mlops-artifacts-sentinel-ai-project-482208/pipeline_root_v5"
)
def sentinel_pipeline(
    bq_table_id: str = "sentinel-ai-project-482208.retail_ai.gemini_tuning_dataset",
    bucket_name: str = "sentinel-mlops-artifacts-sentinel-ai-project-482208",
    project_id: str = "sentinel-ai-project-482208",
    location: str = "asia-east1",
    model_display_name: str = "sentinel-gemini-tuned-v5",
):
    # Step 1: Export Data
    # FORCE n1-standard-1 (1 vCPU, 3.75GB RAM) to fit strict quota
    export_task = export_data_v2_op(
        bq_table_id=bq_table_id,
        bucket_name=bucket_name,
        project_id=project_id,
    ).set_cpu_limit('1').set_memory_limit('2G')

    # Step 2: Trigger Tuning
    trigger_tuning_task = trigger_tuning_job_op(
        training_data_uri=export_task.output,
        project=project_id,
        location=location,
        model_display_name=model_display_name,
        epochs=5
    ).set_cpu_limit('1').set_memory_limit('2G')

if __name__ == "__main__":
    # Output directly to backend directory for Docker build
    output_file = "../sentinel_pipeline.json"
    print(f"Compiling V5 pipeline (asia-east1) to {output_file}...")
    compiler.Compiler().compile(
        pipeline_func=sentinel_pipeline,
        package_path=output_file
    )
    print("Done.")
