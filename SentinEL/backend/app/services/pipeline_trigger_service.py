import google.cloud.aiplatform as aiplatform
from app.core.config import settings
from mlops.retraining_pipeline import retraining_pipeline, compile_pipeline, PIPELINE_ROOT
import os
import logging

logger = logging.getLogger(__name__)

class PipelineTriggerService:
    def __init__(self):
        self.project_id = settings.PROJECT_ID
        self.location = settings.LOCATION
        self.pipeline_root = PIPELINE_ROOT
        
        # Ensure client is initialized
        aiplatform.init(
            project=self.project_id,
            location=self.location,
            staging_bucket=self.pipeline_root
        )

    def trigger_retraining_job(self) -> dict:
        """
        Triggers the continuous training pipeline on Vertex AI.
        """
        try:
            # 1. Compile Pipeline
            pipeline_path = "sentinel_retraining_pipeline.json"
            # Ensure we are in a writable directory or handle path carefully
            # For simplicity, we assume writing to current working dir or temp is fine
            compile_pipeline()
            
            if not os.path.exists(pipeline_path):
                 raise FileNotFoundError(f"Pipeline compilation failed, {pipeline_path} not found.")

            # 2. Submit Job
            job = aiplatform.PipelineJob(
                display_name="sentinel-retraining-trigger",
                template_path=pipeline_path,
                pipeline_root=self.pipeline_root,
                parameter_values={
                    "project_id": self.project_id,
                    "region": self.location,
                    "accuracy_threshold": 0.75
                },
                enable_caching=False
            )
            
            job.submit()
            
            logger.info(f"Pipeline job submitted successfully. Job ID: {job.name}")
            
            return {
                "status": "submitted",
                "job_id": job.name,
                "dashboard_url": job._dashboard_uri()
            }
            
        except Exception as e:
            logger.error(f"Failed to trigger retraining pipeline: {e}")
            raise e

_trigger_service = None

def get_pipeline_trigger_service():
    global _trigger_service
    if not _trigger_service:
        _trigger_service = PipelineTriggerService()
    return _trigger_service
