
import logging
from google.cloud import bigquery
from google.cloud import storage
import json
import traceback

# Mimic the environment
PROJECT_ID = "sentinel-ai-project-482208"
BUCKET_NAME = "sentinel-mlops-artifacts-sentinel-ai-project-482208"
BQ_TABLE_ID = "sentinel-ai-project-482208.retail_ai.gemini_tuning_dataset"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_export_op_logic():
    logger.info("Starting simulation of export_data_op...")
    try:
        # Initialize clients with explicit project
        bq_client = bigquery.Client(project=PROJECT_ID)
        storage_client = storage.Client(project=PROJECT_ID)

        logger.info(f"Reading data from BigQuery table: {BQ_TABLE_ID}")
        
        # Read from BigQuery using standard result() iterator (No Pandas dependency)
        query = f"SELECT * FROM `{BQ_TABLE_ID}` LIMIT 10"
        query_job = bq_client.query(query)
        rows = query_job.result()
        
        # Get column names from schema
        schema = {field.name.lower(): field.name for field in rows.schema}
        logger.info(f"Schema columns found: {list(schema.keys())}")

        jsonl_data = []
        count = 0
        
        for row in rows:
            # Row object behave like a dict?
            # Let's try accessing by key using the schema map
            row_dict = {k.lower(): row[v] for k, v in schema.items()}
            
            # 1. Try 'prompt' and 'response'
            user_content = row_dict.get('prompt') or row_dict.get('input_text') or row_dict.get('input') or row_dict.get('question')
            model_content = row_dict.get('response') or row_dict.get('output_text') or row_dict.get('output') or row_dict.get('answer')
            
            if user_content and model_content:
                entry = {
                    "messages": [
                        {"role": "user", "content": str(user_content)},
                        {"role": "model", "content": str(model_content)}
                    ]
                }
                jsonl_data.append(entry)
                count += 1
            else:
                logger.warning(f"Skipping: {list(row_dict.keys())}")

        if not jsonl_data:
            raise ValueError("Could not extract valid training pairs (input/output) from query results.")

        logger.info(f"Processed {count} valid rows.")

        # Upload to GCS
        file_name = "training_data_debug.jsonl"
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(file_name)

        logger.info(f"Uploading records to gs://{BUCKET_NAME}/{file_name}")
        
        jsonl_string = "\n".join([json.dumps(record) for record in jsonl_data])
        blob.upload_from_string(jsonl_string, content_type="application/jsonl")

        gcs_uri = f"gs://{BUCKET_NAME}/{file_name}"
        logger.info(f"Success! URI: {gcs_uri}")
        return gcs_uri

    except Exception as e:
        logger.error(f"Export Data Op Failed with error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_export_op_logic()
