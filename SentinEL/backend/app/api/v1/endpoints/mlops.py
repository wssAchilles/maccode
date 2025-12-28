from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.services.pipeline_trigger_service import get_pipeline_trigger_service
from app.services.storage_service import get_storage_service
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/retrain", status_code=202)
def trigger_retraining(background_tasks: BackgroundTasks):
    """
    Triggers the automated model retraining pipeline on Vertex AI.
    Returns immediately with a job ID estimation, while the job is submitted.
    """
    service = get_pipeline_trigger_service()
    try:
        # Trigger synchronously for this demo to return the job ID, 
        # or use background tasks if submission takes too long.
        result = service.trigger_retraining_job()
        return result
    except Exception as e:
        logger.error(f"Error triggering retraining: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/audit-logs")
def get_audit_logs():
    """
    Retrieves the latest AI Audit logs (Judge Service results).
    """
    storage = get_storage_service()
    if not storage:
        # Return mock data if storage service is not ready
        return [
            {
                "timestamp": "2024-05-20T10:00:00Z",
                "user_id": "u123",
                "score": 95,
                "reason": "Tone is professional and compliant.",
                "is_compliant": True
            },
             {
                "timestamp": "2024-05-20T10:05:00Z",
                "user_id": "u124",
                "score": 45,
                "reason": "Over-promising on discounts.",
                "is_compliant": False
            }
        ]
    
    try:
        # Fetch real logs from Firestore
        logs = storage.get_recent_audit_logs(limit=20)
        return logs
    except Exception as e:
        logger.error(f"Error fetching audit logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch audit logs")
