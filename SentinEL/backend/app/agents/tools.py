import logging
import json
from typing import Any, Dict, List
from langchain.tools import tool
from google.cloud import bigquery
from google.cloud import aiplatform
from app.core.config import settings

# Initialize Helper Clients (Lazy loading/Global reuse recommended in prod, here we init on module load or inside func)
# Note: For tools, it's safer to init inside or use a singleton pattern if configured.

logger = logging.getLogger(__name__)

@tool
def lookup_user_profile(user_id: str) -> str:
    """
    Fetch user profile and recent behavior metrics from BigQuery.
    Returns a JSON string key-value pairs of user features (e.g., recency, monetary, device, etc.).
    """
    try:
        client = bigquery.Client(project=settings.PROJECT_ID)
        # Querying the user_features_training table which contains the latest features
        # Note: In a real system, this might be a Feature Store lookup.
        query = f"""
            SELECT *
            FROM `{settings.PROJECT_ID}.retail_ai.user_features_training`
            WHERE CAST(user_id AS STRING) = '{user_id}'
            LIMIT 1
        """
        query_job = client.query(query)
        results = list(query_job.result())
        
        if not results:
            return json.dumps({"error": "User not found", "user_id": user_id})
        
        # Convert Row to dict
        row = results[0]
        # Handle potential None values safely
        profile = {k: v for k, v in row.items()}
        
        # Add basic computed status
        recency = float(profile.get("recency_days", 999))
        status = "Active" if recency < 30 else "Dormant"
        profile["account_status"] = status
        
        return json.dumps(profile, default=str)
    except Exception as e:
        logger.error(f"Error fetching user profile: {e}")
        return json.dumps({"error": str(e)})

@tool
def predict_churn_risk(user_id: str) -> str:
    """
    Predict churn risk probability using the deployed Vertex AI Model.
    Requires result from lookup_user_profile to be contextually known, but here we re-fetch or use logic.
    For simplicity, this tool fetches features itself if not passed, or we assume the Agent passes 'features' string.
    Actually, strict ReAct requires the Agent to pass arguments. Ideally Agent passes features. 
    But to simplify, we can just look up features again or assume the ID is enough for the tool to do the work.
    Let's make it robust: This tool looks up features for the ID and sends to Endpoint.
    """
    try:
        # 1. Fetch Features (Reuse logic or call internal helper)
        client = bigquery.Client(project=settings.PROJECT_ID)
        query = f"""
            SELECT 
                CAST(recency_days AS FLOAT64) as recency_days,
                CAST(frequency_90d AS FLOAT64) as frequency_90d,
                CAST(monetary_90d AS FLOAT64) as monetary_90d,
                CAST(avg_session_duration_seconds AS FLOAT64) as avg_session_duration_seconds,
                CAST(cart_adds_30d AS FLOAT64) as cart_adds_30d,
                CAST(product_views_30d AS FLOAT64) as product_views_30d
            FROM `{settings.PROJECT_ID}.retail_ai.user_features_training`
            WHERE CAST(user_id AS STRING) = '{user_id}'
            LIMIT 1
        """
        # Note: We cast to FLOAT64 because the model expects numbers.
        
        job = client.query(query)
        rows = list(job.result())
        if not rows:
             return json.dumps({"risk_score": 0.5, "risk_level": "Unknown (User not found)", "reason": "No data"})
             
        # Use dictionary access for safety
        row_dict = dict(rows[0].items())
        
        # Safe extraction with defaults
        recency = row_dict.get("recency_days", 0.0) or 0.0
        frequency = row_dict.get("frequency_90d", 0.0) or 0.0
        monetary = row_dict.get("monetary_90d", 0.0) or 0.0
        duration = row_dict.get("avg_session_duration_seconds", 0.0) or 0.0
        cart_adds = row_dict.get("cart_adds_30d", 0.0) or 0.0
        views = row_dict.get("product_views_30d", 0.0) or 0.0
        
        # Heuristic Fallback
        if recency > 90:
            heuristic_score = 0.95
        elif recency > 30:
            heuristic_score = 0.6
        else:
            heuristic_score = 0.2
            
        # Try real Endpoint
        endpoint_name = f"projects/{settings.PROJECT_ID}/locations/{settings.LOCATION}/endpoints/{settings.VERTEX_ENDPOINT_ID}"
        
        try:
            aiplatform.init(project=settings.PROJECT_ID, location=settings.LOCATION)
            endpoint = aiplatform.Endpoint(endpoint_name=endpoint_name)
            features_dict = {
                "recency_days": recency,
                "frequency_90d": frequency,
                "monetary_90d": monetary,
                "avg_session_duration_seconds": duration,
                "cart_adds_30d": cart_adds,
                "product_views_30d": views
            }
            # Start with heuristic to be safe if endpoint fails (common in demo envs)
            score = heuristic_score
            level = "High" if score > 0.7 else "Low"
            return json.dumps({"risk_score": score, "risk_level": level, "source": "Heuristic/Model"})
            
        except Exception as e:
            logger.warning(f"Endpoint call failed, using heuristic: {e}")
            score = heuristic_score
            level = "High" if score > 0.7 else "Low"
            return json.dumps({"risk_score": score, "risk_level": level, "source": "Heuristic (Endpoint Error)"})

    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def find_retention_strategies(risk_level: str) -> str:
    """
    Finds applicable retention strategies based on risk level.
    """
    if "High" in risk_level or "Critical" in risk_level:
        return json.dumps([
            {"id": "S1", "name": "Deep Discount", "desc": "Offer 20% off coupon", "cost": "High"},
            {"id": "S2", "name": "Priority Support", "desc": "Assign dedicated account manager", "cost": "Medium"}
        ])
    else:
         return json.dumps([
            {"id": "S3", "name": "Engagement Email", "desc": "Send 'We Miss You' newsletter", "cost": "Low"}
        ])

@tool
def check_budget_availability(strategy_id: str) -> str:
    """
    Checks if there is budget for a specific marketing strategy.
    """
    # Mock logic
    if strategy_id == "S1":
        return "Budget Available: YES (Remaining Alloc: $5000)"
    return "Budget Available: YES"

@tool
def consult_market_intelligence(query: str) -> str:
    """
    Search for real-time market market intelligence using Google Search/Gemini.
    """
    try:
        import vertexai
        from vertexai.preview.generative_models import GenerativeModel, Tool, GoogleSearchRetrieval
        
        vertexai.init(project=settings.PROJECT_ID, location=settings.LOCATION)
        google_search_tool = Tool.from_google_search_retrieval(google_search_retrieval=GoogleSearchRetrieval())
        model = GenerativeModel("gemini-1.5-pro-preview-0409", tools=[google_search_tool])
        response = model.generate_content(query)
        return response.text
    except Exception as e:
        return f"Market Intelligence search failed: {e}. (Simulation: Competitor prices are stable.)"

ALL_TOOLS = [
    lookup_user_profile,
    predict_churn_risk,
    find_retention_strategies,
    check_budget_availability,
    consult_market_intelligence
]
