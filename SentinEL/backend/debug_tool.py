
import os
import sys
import json
from google.cloud import bigquery
from app.core.config import settings

# Mock settings just in case, though imports should work if path is right.
os.environ["GOOGLE_CLOUD_PROJECT"] = "sentinel-ai-project-482208"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"

def test_lookup_user_profile(user_id: str):
    print(f"Testing lookup_user_profile for {user_id}...")
    try:
        client = bigquery.Client(project=settings.PROJECT_ID)
        query = f"""
            SELECT *
            FROM `{settings.PROJECT_ID}.retail_ai.user_features_training`
            WHERE CAST(user_id AS STRING) = '{user_id}'
            LIMIT 1
        """
        print(f"Running query: {query}")
        query_job = client.query(query)
        results = list(query_job.result())
        
        if not results:
            print("User not found.")
            return

        row = results[0]
        profile = {k: v for k, v in row.items()}
        print("Profile found:")
        print(json.dumps(profile, default=str, indent=2))
        
        recency = float(profile.get("recency_days", 999))
        print(f"Recency: {recency}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Add backend path to sys.path
    sys.path.append(os.path.join(os.getcwd()))
    
    test_lookup_user_profile("20671")
