from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class AnalyzeUserRequest(BaseModel):
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
