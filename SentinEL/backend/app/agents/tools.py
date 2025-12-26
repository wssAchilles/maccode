import logging
import random
from typing import Dict, Any, List

from langchain.tools import tool
from pydantic import BaseModel, Field

from app.services.prediction_service import get_prediction_service
from app.services.recommendation_service import get_recommendation_service

logger = logging.getLogger(__name__)

# ==============================================================================
# Input Schemas
# ==============================================================================

class UserProfileInput(BaseModel):
    user_id: str = Field(description="The unique identifier of the user to look up.")

class ChurnRiskInput(BaseModel):
    user_id: str = Field(description="The ID of the user.")
    events: List[str] = Field(description="List of recent user event names (e.g., 'page_view', 'add_to_cart').")

class RetentionStrategiesInput(BaseModel):
    user_id: str = Field(description="The ID of the user.")
    risk_score: float = Field(description="The predicted churn risk score (0.0 to 1.0).")

class BudgetCheckInput(BaseModel):
    strategy_cost: float = Field(description="The estimated cost of the retention strategy.")

# ==============================================================================
# Tool Definitions
# ==============================================================================

@tool("lookup_user_profile", args_schema=UserProfileInput)
def lookup_user_profile(user_id: str) -> Dict[str, Any]:
    """
    Look up user profile data from the feature store (Mock implementation).
    Returns user demographics, recent activity summary, and membership status.
    """
    logger.info(f"[Tool] lookup_user_profile called for user_id={user_id}")
    
    # Mock Data: 模拟不同用户的 Feature
    # 实际项目中应调用 FeatureStoreService
    
    # 确定性 Mock: 根据 ID 尾号决定用户类型
    last_digit = int(user_id[-1]) if user_id[-1].isdigit() else 0
    
    if last_digit % 3 == 0:
        # High Value User
        profile = {
            "user_id": user_id,
            "segment": "VIP",
            "lifetime_value": 1200.50,
            "membership_level": "Gold",
            "last_active_days_ago": 2,
            "recent_events": ["page_view", "view_item", "add_to_cart", "remove_from_cart", "page_view"]
        }
    elif last_digit % 3 == 1:
        # At Risk User
        profile = {
            "user_id": user_id,
            "segment": "At-Risk",
            "lifetime_value": 450.00,
            "membership_level": "Silver",
            "last_active_days_ago": 15,
            "recent_events": ["page_view", "check_policy", "view_returns", "page_view"]
        }
    else:
        # New/Low Value User
        profile = {
            "user_id": user_id,
            "segment": "New",
            "lifetime_value": 0.00,
            "membership_level": "Basic",
            "last_active_days_ago": 0,
            "recent_events": ["session_start", "page_view"]
        }
        
    logger.info(f"[Tool] lookup_user_profile result: {profile}")
    return profile


@tool("predict_churn_risk", args_schema=ChurnRiskInput)
def predict_churn_risk(user_id: str, events: List[str]) -> Dict[str, Any]:
    """
    Predict the churn probability for a user based on their recent event sequence.
    Uses the Vertex AI Churn Prediction Endpoint.
    """
    logger.info(f"[Tool] predict_churn_risk called for user_id={user_id}, events_len={len(events)}")
    
    service = get_prediction_service()
    if not service:
        # Fallback if service not init
        return {"risk_score": 0.5, "risk_level": "Medium", "error": "Service Unavailable"}

    # 同步调用 (LangChain Tools 默认是同步的，若需异步可使用 acheck_budget_availability 等 async compat)
    # 由于底层 predict_churn 是同步网络调用，这里会阻塞。
    # 生产环境建议使用 async tool 结合 LangGraph 的 async 执行。
    
    try:
        score = service.predict_churn(user_id, events)
        level = service.get_risk_level(score)
        
        result = {
            "risk_score": score,
            "risk_level": level
        }
        logger.info(f"[Tool] predict_churn_risk result: {result}")
        return result
        
    except Exception as e:
        logger.error(f"[Tool] predict_churn_risk failed: {e}")
        return {"risk_score": 0.5, "risk_level": "Medium", "error": str(e)}


@tool("find_retention_strategies", args_schema=RetentionStrategiesInput)
async def find_retention_strategies(user_id: str, risk_score: float) -> List[Dict[str, Any]]:
    """
    Find personalized retention strategies using Two-Tower Recommendation System (Vector Search).
    Strategies are retrieved based on user embedding and risk profile.
    NOTE: This is an ASYNC tool.
    """
    logger.info(f"[Tool] find_retention_strategies called for user_id={user_id}, risk={risk_score}")
    
    service = get_recommendation_service()
    if not service:
        return []
        
    try:
        recommendations = await service.get_recommendations(user_id, risk_score)
        logger.info(f"[Tool] find_retention_strategies found {len(recommendations)} strategies")
        return recommendations
    except Exception as e:
        logger.error(f"[Tool] find_retention_strategies failed: {e}")
        return []


@tool("check_budget_availability", args_schema=BudgetCheckInput)
def check_budget_availability(strategy_cost: float) -> Dict[str, Any]:
    """
    Check if there is enough marketing budget to execute a specific strategy.
    """
    logger.info(f"[Tool] check_budget_availability called for cost={strategy_cost}")
    
    # Mock Logic: Budgets are tight!
    # Randomly approve or reject to make it interesting, or base on cost thresholds
    
    MAX_AUTO_APPROVE_COST = 50.0
    
    if strategy_cost <= MAX_AUTO_APPROVE_COST:
        approved = True
        reason = "Cost is within auto-approval limit."
    else:
        # 30% chance of approval for high cost
        import random
        approved = random.random() > 0.7
        reason = "Budget allocation check." if approved else "Cost exceeds current allocation limit."
        
    return {
        "approved": approved,
        "reason": reason,
        "requested_cost": strategy_cost
    }

# Export all tools
ALL_TOOLS = [
    lookup_user_profile,
    predict_churn_risk,
    find_retention_strategies,
    check_budget_availability
]
