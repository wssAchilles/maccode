import os
import sys
from google.cloud import bigquery
from datetime import datetime, timezone

# Add parent dir to sys.path to allow importing from app.core.config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app.core.config import settings
except ImportError:
    # Fallback config if running standalone without app context
    class Settings:
        PROJECT_ID = "sentinel-ai-project-482208"
        DATASET_ID = "sentinel_analytics"
    settings = Settings()

def rejuvenate_data():
    """
    Shifts historical data in BigQuery to the present to simulate a live system.
    """
    client = bigquery.Client(project=settings.PROJECT_ID)
    dataset_id = getattr(settings, "DATASET_ID", "retail_ai")
    
    print(f"🚀 Starting Data Rejuvenation for project: {settings.PROJECT_ID}, dataset: {dataset_id}")

    # 1. Get max timestamp from events
    query_max_ts = f"""
        SELECT MAX(created_at) as max_ts
        FROM `{settings.PROJECT_ID}.{dataset_id}.events`
    """
    
    try:
        query_job = client.query(query_max_ts)
        results = list(query_job.result())
        
        if not results or results[0].max_ts is None:
            print("⚠️ No data found in events table or max_ts is NULL. Aborting.")
            return

        max_ts = results[0].max_ts
        print(f"📅 Current Data Max Timestamp: {max_ts}")
        
    except Exception as e:
        print(f"❌ Error querying max timestamp: {e}")
        return

    # 2. Calculate Delta (Shift to yesterday to be safe, or just now)
    # Goal: Max TS -> Current Date - 1 Hour (to keep it very fresh but slightly past)
    # Using CURRENT_TIMESTAMP() in SQL is easier for the shift calculation.
    
    # We will compute the shift in seconds inside BigQuery to avoid timezone complexities in Python
    # Shift = CURRENT_TIMESTAMP() - MAX(created_at)
    
    print("⏳ Calculating time shift and executing CTAS for 'events' table...")

    # Strategy: Create a new table 'events_new' with shifted timestamps, then swap.
    # We use TIMESTAMP_ADD(created_at, INTERVAL shift_seconds SECOND)
    
    rejuvenate_events_sql = f"""
    DECLARE max_ts TIMESTAMP;
    DECLARE shift_seconds INT64;

    SET max_ts = (SELECT MAX(created_at) FROM `{settings.PROJECT_ID}.{dataset_id}.events`);
    
    -- Shift so the latest event happened 1 hour ago
    SET shift_seconds = TIMESTAMP_DIFF(TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR), max_ts, SECOND);

    CREATE OR REPLACE TABLE `{settings.PROJECT_ID}.{dataset_id}.events` AS
    SELECT 
        * REPLACE (
            TIMESTAMP_ADD(created_at, INTERVAL shift_seconds SECOND) AS created_at
        )
    FROM `{settings.PROJECT_ID}.{dataset_id}.events`;
    
    SELECT shift_seconds;
    """
    
    try:
        query_job = client.query(rejuvenate_events_sql)
        # Wait for result to ensure 'events' is updated before updating profiles
        rows = list(query_job.result())
        # shift_seconds = rows[0].shift_seconds # commented out to avoid potential attribute error if select result structure differs or iterate
        print(f"✅ 'events' table rejuvenated! Time shifted.")
    except Exception as e:
        print(f"❌ Error updating 'events' table: {e}")
        return

    # 3. Update User Profiles
    # user_profiles table not found in inspect_schema, skipping to avoid errors.
    print("⚠️ Skipping 'user_profiles' update as table was not found or schema mismatch.")

        
    print("🎉 Data Rejuvenation Complete!")

if __name__ == "__main__":
    rejuvenate_data()
