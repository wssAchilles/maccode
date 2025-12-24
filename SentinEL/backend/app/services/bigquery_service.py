"""
BigQuery Service - 企业级用户流失预测和向量检索服务

包含 OpenTelemetry 手动埋点，用于 Google Cloud Trace 可视化。
"""

from google.cloud import bigquery
from fastapi import HTTPException
from opentelemetry import trace
import os

# 获取 Tracer 实例
tracer = trace.get_tracer(__name__)


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
        使用 BigQuery ML 预测用户流失风险。
        
        Trace Span: "BigQuery: ML.PREDICT"
        """
        # 创建追踪 Span
        with tracer.start_as_current_span("BigQuery: ML.PREDICT") as span:
            # 添加 Span 属性用于调试
            span.set_attribute("db.system", "bigquery")
            span.set_attribute("db.operation", "ML.PREDICT")
            span.set_attribute("user.id", user_id)
            span.set_attribute("model.name", self.prediction_model)
            
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
                    span.set_attribute("error", True)
                    span.set_attribute("error.message", "User not found")
                    raise HTTPException(status_code=404, detail=f"User {user_id} not found in features table.")
                    
                row = rows[0]
                
                # Extract probability for label 1 (Churn)
                churn_prob = 0.0
                for p in row.predicted_churn_label_probs:
                    label = p['label'] if isinstance(p, dict) else p.label
                    prob = p['prob'] if isinstance(p, dict) else p.prob
                    
                    if label == 1:
                        churn_prob = prob
                        break
                
                # 记录结果到 Span
                span.set_attribute("prediction.churn_probability", churn_prob)
                span.set_attribute("prediction.label", row.predicted_churn_label)
                        
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
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                print(f"Error in BigQuery Service (Prediction): {e}")
                raise HTTPException(status_code=500, detail="Internal ML prediction error.")

    def search_similar_policies(self, query_vector: list[float], top_k: int = 3) -> list[str]:
        """
        使用向量搜索检索相关挽留策略。
        
        Trace Span: "BigQuery: Vector Search"
        """
        # 创建追踪 Span
        with tracer.start_as_current_span("BigQuery: Vector Search") as span:
            span.set_attribute("db.system", "bigquery")
            span.set_attribute("db.operation", "VECTOR_SEARCH")
            span.set_attribute("search.top_k", top_k)
            span.set_attribute("search.vector_dimensions", len(query_vector))
            
            try:
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
                
                # 记录结果到 Span
                span.set_attribute("search.results_count", len(results))
                
                return results

            except Exception as e:
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                print(f"Error in BigQuery Service (Vector Search): {e}")
                return []

