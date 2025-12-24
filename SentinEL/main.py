import os
import vertexai
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google.cloud import bigquery
from vertexai.generative_models import GenerativeModel
from vertexai.language_models import TextEmbeddingModel

# --- Configuration ---
PROJECT_ID = "sentinel-ai-project-482208"
LOCATION = "us-central1"
BQ_DATASET = "retail_ai"
MODEL_PREDICTION_ENDPOINT = f"{PROJECT_ID}.{BQ_DATASET}.churn_dnn_premium"
USER_FEATURES_TABLE = f"{PROJECT_ID}.{BQ_DATASET}.user_features_training"
POLICY_TABLE_EMBEDDED = f"{PROJECT_ID}.{BQ_DATASET}.retention_policies_embedded"

# Initialize Clients
bq_client = bigquery.Client(project=PROJECT_ID)
vertexai.init(project=PROJECT_ID, location=LOCATION)

# 加载 Gemini Pro 模型 (User requested top-tier model)
MODEL_ID = "gemini-2.5-pro"
generative_model = GenerativeModel(MODEL_ID)
embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")

# Initialize FastAPI app
app = FastAPI(
    title="SentinEL Retention Agent",
    description="AI Agent for High-Value Customer Retention",
    version="1.0.0"
)

# --- Pydantic Models ---
class AnalyzeUserRequest(BaseModel):
    user_id: str

class RetentionResponse(BaseModel):
    user_id: str
    risk_level: str
    churn_probability: float
    recommended_action: str
    generated_email: str | None = None
    retention_policies: list[str] | None = None

# --- Tools ---

def get_user_risk_profile(user_id: str) -> dict:
    """
    Retrieves user risk profile and features using BigQuery ML prediction.
    """
    query = f"""
        SELECT
            *
        FROM
            ML.PREDICT(MODEL `{MODEL_PREDICTION_ENDPOINT}`,
            (
                SELECT * EXCEPT(churn_label)
                FROM `{USER_FEATURES_TABLE}`
                WHERE user_id = {user_id}
            ))
    """
    try:
        query_job = bq_client.query(query)
        rows = list(query_job.result())
        
        if not rows:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found in features table.")
            
        row = rows[0]
        
        # Extract probability for label 1 (Churn)
        # ML.PREDICT returns 'predicted_churn_label' and 'predicted_churn_label_probs'
        # probs is an array of structs: [{label: 0, prob: ...}, {label: 1, prob: ...}]
        churn_prob = 0.0
        for p in row.predicted_churn_label_probs:
            # Structs in arrays are returned as dicts
            label = p['label'] if isinstance(p, dict) else p.label
            prob = p['prob'] if isinstance(p, dict) else p.prob
            
            if label == 1:
                churn_prob = prob
                break
                
        return {
            "user_id": user_id,
            "predicted_label": row.predicted_churn_label,
            "churn_probability": churn_prob,
            "features": {
                "country": row.country,
                "traffic_source": row.traffic_source,
                "device_type": row.device_type,
                "monetary_90d": row.monetary_90d
            }
        }
        
    except Exception as e:
        # Re-raise HTTP exceptions, wrap others
        if isinstance(e, HTTPException):
            raise e
        print(f"Error in get_user_risk_profile: {e}")
        raise HTTPException(status_code=500, detail="Internal ML prediction error.")

def search_retention_policy(query_text: str, top_k: int = 3) -> list[str]:
    """
    Searches for relevant retention policies using Vector Search.
    
    NOTE: Using exact search simulation for small datasets if needed, 
    but strictly implementing VECTOR_SEARCH logic as requested.
    """
    try:
        # 1. Generate Embedding
        embeddings = embedding_model.get_embeddings([query_text])
        query_vector = embeddings[0].values
        
        # 2. Vector Search Query
        # Using pure SQL VECTOR_SEARCH if available, or Cosine Distance manually for small data
        # Since we skipped index creation for small data, we use VECTOR_SEARCH with brute force (which is default without index)
        # or manual cosine distance for absolute certainty in this demo.
        # Let's use the standard VECTOR_SEARCH syntax which works for both indexed and non-indexed (exact).
        
        sql = f"""
            SELECT base.policy_text
            FROM
              VECTOR_SEARCH(
                TABLE `{POLICY_TABLE_EMBEDDED}`,
                'ml_generate_embedding_result',
                (SELECT {query_vector} AS query_vector),
                top_k => {top_k},
                distance_type => 'COSINE'
              )
        """
        
        query_job = bq_client.query(sql)
        results = [row.policy_text for row in query_job.result()]
        return results

    except Exception as e:
        print(f"Error in search_retention_policy: {e}")
        # Fallback empty list or specific error handling
        return []

# --- API Endpoints ---

@app.post("/analyze_user", response_model=RetentionResponse)
def analyze_user(request: AnalyzeUserRequest):
    """
    Analyzes a user's churn risk and generates a retention plan if necessary.
    """
    user_id = request.user_id
    
    # 1. Get Risk Profile
    profile = get_user_risk_profile(user_id)
    churn_label = profile["predicted_label"]
    feature_context = profile["features"]
    
    # 2. Logic Check
    if churn_label == 0:
        return RetentionResponse(
            user_id=user_id,
            risk_level="Low",
            churn_probability=profile["churn_probability"],
            recommended_action="No intervention needed"
        )
        
    # 3. High Risk: Retrieve Policies
    # Construct a query based on user features to find relevant policies
    search_query = f"Customer from {feature_context['country']} via {feature_context['traffic_source']} spending {feature_context['monetary_90d']}"
    policies = search_retention_policy(search_query, top_k=3)
    
    # 4. Generate Email with Gemini
    system_prompt = """
    你是一个高级客户关系专家 (SentinEL)。你的目标是根据数据和公司政策挽留高价值客户。
    严禁编造优惠政策，必须基于工具检索到的信息。
    语气要诚恳、专业且具有个性化。
    """
    
    user_prompt = f"""
    客户画像:
    - ID: {user_id}
    - 国家: {feature_context['country']}
    - 来源: {feature_context['traffic_source']}
    - 过去90天消费: {feature_context['monetary_90d']}
    - 风险概率: {profile['churn_probability']:.2f}

    检索到的公司挽留政策:
    {chr(10).join([f"- {p}" for p in policies])}

    任务:
    请为该客户起草一封挽留邮件。
    1. 针对其具体情况（如高消费、地区等）进行个性化问候。
    2. 巧妙地提供上述政策中适用的权益。
    3. 保持简短有力。
    """
    
    generation_config = {
        "temperature": 0.7,
        "max_output_tokens": 500,
    }
    
    response = generative_model.generate_content(
        [system_prompt, user_prompt],
        generation_config=generation_config
    )
    
    generated_text = response.text
    
    return RetentionResponse(
        user_id=user_id,
        risk_level="High",
        churn_probability=profile["churn_probability"],
        recommended_action="Send Retention Email",
        retention_policies=policies,
        generated_email=generated_text
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
