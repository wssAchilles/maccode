from google.cloud import bigquery
import os
import sys

# Add parent dir to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def inspect_schema():
    project_id = "sentinel-ai-project-482208"
    dataset_id = "retail_ai"
    table_id = "user_features_training"
    
    client = bigquery.Client(project=project_id)
    table_ref = f"{project_id}.{dataset_id}.{table_id}"
    
    print(f"Inspecting table: {table_ref}")
    try:
        table = client.get_table(table_ref)
        print("\nSchema:")
        for schema_field in table.schema:
            print(f" - {schema_field.name} ({schema_field.field_type})")
    except Exception as e:
        print(f"Error getting table: {e}")

if __name__ == "__main__":
    inspect_schema()
