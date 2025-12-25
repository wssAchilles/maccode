from fastapi import APIRouter, Depends, HTTPException, Header
from app.services.pipeline_service import PipelineService
from app.core.security import verify_api_key
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/train")
async def trigger_training_pipeline(
    api_key: str = Depends(verify_api_key)
):
    """
    Triggers the Vertex AI training pipeline.
    Requires a valid API key.
    """
    try:
        pipeline_service = PipelineService()
        job_id, dashboard_url = pipeline_service.submit_training_job()
        
        return {
            "status": "Training Initiated",
            "job_id": job_id,
            "console_url": dashboard_url,
            "message": "Vertex AI pipeline job submitted successfully."
        }
    except Exception as e:
        logger.error(f"Failed to trigger pipeline: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger pipeline: {str(e)}")

@router.get("/train/{job_id}")
async def get_training_status(
    job_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Get the status of a specific training job.
    """
    try:
        pipeline_service = PipelineService()
        # Decode the job_id if it was URL encoded (though usually passed as path param ok)
        # The job_id from Vertex SDK is a full resource name path, client needs to handle it or we pass it directly
        # Example job_id: projects/672705370432/locations/us-central1/pipelineJobs/sentinel-continuous-training-pipeline-20251225123659
        
        status = pipeline_service.get_job_status(job_id)
        return {"job_id": job_id, "status": status}
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")
