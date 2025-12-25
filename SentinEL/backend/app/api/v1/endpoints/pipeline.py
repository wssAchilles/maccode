from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from app.services.data_factory_service import DataFactory
from app.core.security import verify_api_key
import logging
import uuid

router = APIRouter()
logger = logging.getLogger(__name__)

# Single instance of DataFactory
try:
    data_factory = DataFactory()
except Exception as e:
    logger.error(f"Failed to initialize DataFactory at module level: {e}")
    data_factory = None

async def run_pipeline_task(job_id: str):
    logger.info(f"Job {job_id}: Starting Data Factory Pipeline Task...")
    if data_factory:
        try:
            result = await data_factory.run_pipeline()
            logger.info(f"Job {job_id}: Pipeline finished. Result: {result}")
        except Exception as e:
            logger.error(f"Job {job_id}: Pipeline failed: {e}")
    else:
        logger.error(f"Job {job_id}: DataFactory not initialized.")

@router.post("/run_data_pipeline", dependencies=[Depends(verify_api_key)])
async def trigger_data_pipeline(background_tasks: BackgroundTasks):
    """
    Triggers the Data Factory pipeline to fetch low-quality logs,
    synthesize better data using Gemini, and export to BigQuery.
    """
    if not data_factory:
        raise HTTPException(status_code=503, detail="Data Factory Service unavailable")

    job_id = str(uuid.uuid4())
    
    background_tasks.add_task(run_pipeline_task, job_id)
    
    return {
        "status": "Pipeline started",
        "job_id": job_id,
        "message": "Data Factory is refining low-quality samples in the background."
    }
