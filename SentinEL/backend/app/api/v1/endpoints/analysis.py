from fastapi import APIRouter, HTTPException
from app.models.schemas import AnalyzeUserRequest, UserAnalysisResponse
from app.services.orchestrator import AnalysisOrchestrator

router = APIRouter()
orchestrator = AnalysisOrchestrator()

@router.post("/analyze", response_model=UserAnalysisResponse)
def analyze_user_endpoint(request: AnalyzeUserRequest):
    """
    **Analyzes user retention risk and generates intervention strategies.**

    - **Low Risk**: Returns risk profile only.
    - **High Risk**: Performs RAG (Retrieval-Augmented Generation) to find policies and generates a personalized email.
    """
    try:
        result = orchestrator.analyze_user_workflow(request.user_id)
        return UserAnalysisResponse(**result)
    except Exception as e:
        # Check if it is a 404 (e.g. from BQ service)
        if hasattr(e, "status_code") and e.status_code == 404:
             raise HTTPException(status_code=404, detail=e.detail)
             
        # Log error in production logging system
        print(f"Endpoint Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during analysis.")
