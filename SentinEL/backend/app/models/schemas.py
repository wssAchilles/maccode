from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class UserAnalysisRequest(BaseModel):
    user_id: str
    image_data: Optional[str] = None  # Base64 encoded image

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
    # Multimodal Output
    call_script: Optional[str] = None
    generated_audio: Optional[str] = None  # Base64 encoded MP3

class FeedbackRequest(BaseModel):
    analysis_id: str
    user_id: str
    feedback_type: str  # "thumbs_up" or "thumbs_down"
