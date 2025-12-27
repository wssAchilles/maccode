import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Google Cloud Config
    PROJECT_ID: str = os.getenv("GOOGLE_CLOUD_PROJECT", "sentinel-ai-project-482208")
    LOCATION: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")  # Vertex AI Endpoints 区域
    VERSION: str = "2.0.0"
    
    # Storage Config
    # Defaulting to values found in existing code to ensure backward compatibility if env vars are missing
    PIPELINE_ROOT_BUCKET: str = "sentinel-ai-project-482208_cloudbuild/pipeline_root" 
    MLOPS_ARTIFACT_BUCKET: str = "sentinel-mlops-artifacts-sentinel-ai-project-482208"
    
    # BigQuery Config
    BQ_TUNING_DATASET_ID: str = "sentinel-ai-project-482208.retail_ai.gemini_tuning_dataset"

    model_config = {
        "env_file": ".env",
        "case_sensitive": True
    }

settings = Settings()
