from google.cloud import bigquery
from fastapi import HTTPException
import os

class BigQueryService:
    def __init__(self):
        # Configuration
        self.project_id = "sentinel-ai-project-482208"  # Should ideally load from env
        self.dataset_id = "retail_ai"
        self.client = bigquery.Client(project=self.project_id)
        
        # Table References
        self.prediction_model = f"{self.project_id}.{self.dataset_id}.churn_dnn_premium"
        self.feature_table = f"{self.project_id}.{self.dataset_id}.user_features_training"
        self.policy_table = f"{self.project_id}.{self.dataset_id}.retention_policies_embedded"

    def get_user_churn_prediction(self, user_id: str) -> dict:
        """
        Retrieves user risk profile and features using BigQuery ML prediction.
        """
        query = f"""
            SELECT
                *
            FROM
                ML.PREDICT(MODEL `{self.prediction_model}`,
                (
                    SELECT * EXCEPT(churn_label)
                    FROM `{self.feature_table}`
                    WHERE user_id = {user_id}
                ))
        """
        try:
            query_job = self.client.query(query)
            rows = list(query_job.result())
            
            if not rows:
                # Logically, if user not found in feature table, we can't predict.
                # In real app, might want to return default valid 'low risk' or 404.
                # For this refactor, we stick to 404 to be safe.
                raise HTTPException(status_code=404, detail=f"User {user_id} not found in features table.")
                
            row = rows[0]
            
            # Extract probability for label 1 (Churn)
            churn_prob = 0.0
            for p in row.predicted_churn_label_probs:
                # BigQuery Row iterator returns objects that behave like namespaces but p might be struct
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
            if isinstance(e, HTTPException):
                raise e
            print(f"Error in BigQuery Service (Prediction): {e}")
            raise HTTPException(status_code=500, detail="Internal ML prediction error.")

    def search_similar_policies(self, query_vector: list[float], top_k: int = 3) -> list[str]:
        """
        Searches for relevant retention policies using Vector Search.
        """
        try:
            # We must format the list as a string representation of an array for SQL
            # e.g. [0.1, 0.2, ...]
            vector_str = str(query_vector)
            
            sql = f"""
                SELECT base.policy_text
                FROM
                  VECTOR_SEARCH(
                    TABLE `{self.policy_table}`,
                    'ml_generate_embedding_result',
                    (SELECT {vector_str} AS query_vector),
                    top_k => {top_k},
                    distance_type => 'COSINE'
                  )
            """
            
            query_job = self.client.query(sql)
            results = [row.policy_text for row in query_job.result()]
            return results

        except Exception as e:
            print(f"Error in BigQuery Service (Vector Search): {e}")
            return []  # Fail gracefully with empty policies rather than crashing flow
