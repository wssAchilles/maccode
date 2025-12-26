from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agents.sentinel_agent import invoke_agent

router = APIRouter()

# ==============================================================================
# Models
# ==============================================================================

class AnalyzeFlowRequest(BaseModel):
    user_id: str = Field(..., description="The ID of the user to analyze.")

class TraceStepModel(BaseModel):
    step: int
    type: str # "thought", "action", "observation"
    content: str
    tool: Optional[str] = None
    input: Optional[str] = None

class AnalyzeFlowResponse(BaseModel):
    final_result: str
    trace_log: List[TraceStepModel]

# ==============================================================================
# Endpoints
# ==============================================================================

@router.post("/analyze_flow", response_model=AnalyzeFlowResponse)
async def analyze_user_flow(request: AnalyzeFlowRequest) -> Any:
    """
    Trigger the AI Agent to analyze a user's churn risk and suggest retention strategies.
    Returns the final recommendation along with the detailed reasoning trace log.
    """
    try:
        result = await invoke_agent(request.user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")
