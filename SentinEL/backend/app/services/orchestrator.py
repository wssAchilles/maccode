from app.services.bigquery_service import BigQueryService
from app.services.llm_service import LLMService

class AnalysisOrchestrator:
    def __init__(self):
        self.bq_service = BigQueryService()
        self.llm_service = LLMService()

    def analyze_user_workflow(self, user_id: str) -> dict:
        """
        Orchestrates the entire user analysis and retention workflow.
        """
        # 1. Get Risk Profile from BigQuery
        profile = self.bq_service.get_user_churn_prediction(user_id)
        churn_prob = profile.get("churn_probability", 0.0)
        risk_level = "High" if profile.get("predicted_label") == 1 else "Low"
        
        feature_context = profile.get("features", {})
        
        # Default response structure
        result = {
            "user_id": user_id,
            "risk_level": risk_level,
            "churn_probability": churn_prob,
            "user_features": feature_context,
            "retention_policies": [],
            "generated_email": None,
            "recommended_action": "No intervention needed"
        }

        # 2. Logic Check: Only proceed for High Risk users
        if risk_level == "Low":
            return result
            
        result["recommended_action"] = "Send Retention Email"
        
        # 3. Formulate Search Query for RAG
        # Construct a query based on user features
        country = feature_context.get('country', 'global')
        source = feature_context.get('traffic_source', 'general')
        spend = feature_context.get('monetary_90d', 0)
        
        search_query_text = f"Customer from {country} via {source} spending {spend}"
        
        # 4. Get Embeddings & Search Policies
        query_vector = self.llm_service.get_text_embedding(search_query_text)
        policies = self.bq_service.search_similar_policies(query_vector, top_k=3)
        
        result["retention_policies"] = policies
        
        # 5. Generate Email
        email_content = self.llm_service.generate_retention_email(profile, policies)
        result["generated_email"] = email_content
        
        return result
