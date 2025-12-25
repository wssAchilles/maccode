from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class UserAnalysisRequest(BaseModel):
    user_id: str

class UserAnalysisResponse(BaseModel):
    user_id: str
    risk_level: str
    churn_probability: float
    recommended_action: str
    # Making these optional as low risk users won't have them
    generated_email: Optional[str] = None
    retention_policies: Optional[List[str]] = None
    user_features: Optional[Dict[str, Any]] = None
    analysis_id: Optional[str] = None  # Added for feedback correlation

class FeedbackRequest(BaseModel):
    analysis_id: str
    user_id: str
    feedback_type: str  # "thumbs_up" or "thumbs_down"
