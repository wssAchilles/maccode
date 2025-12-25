
import logging
import pandas as pd
from google.cloud import bigquery
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_export_logic():
    project_id = "sentinel-ai-project-482208"
    dataset_id = "retail_ai"
    table_id = "gemini_tuning_dataset"
    table_ref = f"{project_id}.{dataset_id}.{table_id}"
    
    logger.info(f"Connecting to BigQuery table: {table_ref}")
    
    try:
        client = bigquery.Client(project=project_id)
        query = f"SELECT * FROM `{table_ref}` LIMIT 10"
        df = client.query(query).to_dataframe()
        
        logger.info(f"Successfully fetched {len(df)} rows.")
        logger.info(f"Columns: {df.columns.tolist()}")
        logger.info("First 5 rows:")
        print(df.head())
        
        # Test the extraction logic exactly as in pipeline_def.py
        logger.info("Testing extraction logic...")
        
        jsonl_data = []
        for i, row in df.iterrows():
            row_lower = {k.lower(): v for k, v in row.items()}
            
            user_content = row_lower.get('prompt') or row_lower.get('input_text') or row_lower.get('input') or row_lower.get('question')
            model_content = row_lower.get('response') or row_lower.get('output_text') or row_lower.get('output') or row_lower.get('answer')
            
            if user_content and model_content:
                entry = {
                    "messages": [
                        {"role": "user", "content": str(user_content)},
                        {"role": "model", "content": str(model_content)}
                    ]
                }
                jsonl_data.append(entry)
            else:
                logger.warning(f"Row {i} skipped. Missing content. Keys found: {list(row_lower.keys())}")
                logger.warning(f"Row {i} content: {row.to_dict()}")

        if not jsonl_data:
            logger.error("FAILED: No valid training pairs extracted.")
        else:
            logger.info(f"SUCCESS: Extracted {len(jsonl_data)} valid pairs.")
            print(jsonl_data[0])

    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    test_export_logic()
