from google.cloud import bigquery
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def list_tables():
    project_id = "sentinel-ai-project-482208"
    dataset_id = "retail_ai"
    
    client = bigquery.Client(project=project_id)
    dataset_ref = f"{project_id}.{dataset_id}"
    
    print(f"Listing tables in: {dataset_ref}")
    try:
        tables = client.list_tables(dataset_ref)
        for table in tables:
            print(f" - {table.table_id}")
    except Exception as e:
        print(f"Error listing tables: {e}")

if __name__ == "__main__":
    list_tables()
