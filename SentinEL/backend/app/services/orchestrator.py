"""
SentinEL 业务编排器
协调 BigQuery, LLM 和 Storage 服务完成用户分析流程
"""

import time
from typing import Optional, Callable
from app.services.bigquery_service import BigQueryService
from app.services.llm_service import LLMService
from app.services.storage_service import storage_service


class AnalysisOrchestrator:
    """
    分析编排器
    负责协调各个服务完成完整的用户分析和挽留流程
    """
    
    def __init__(self):
        self.bq_service = BigQueryService()
        self.llm_service = LLMService()

    def analyze_user_workflow(
        self,
        user_id: str,
        background_save: Optional[Callable] = None
    ) -> dict:
        """
        编排完整的用户分析和挽留工作流
        
        Args:
            user_id: 目标用户 ID
            background_save: 可选的后台保存回调函数 (用于 BackgroundTasks)
        
        Returns:
            dict: 分析结果，包含风险评估、RAG 策略和生成的邮件
        """
        # 记录开始时间
        start_time = time.time()
        
        # 1. 从 BigQuery 获取用户风险画像
        profile = self.bq_service.get_user_churn_prediction(user_id)
        churn_prob = profile.get("churn_probability", 0.0)
        risk_level = "High" if profile.get("predicted_label") == 1 else "Low"
        
        feature_context = profile.get("features", {})
        
        # 构建默认响应结构
        result = {
            "user_id": user_id,
            "risk_level": risk_level,
            "churn_probability": churn_prob,
            "user_features": feature_context,
            "retention_policies": [],
            "generated_email": None,
            "recommended_action": "No intervention needed"
        }

        # 2. 逻辑检查: 仅对高风险用户进行干预
        if risk_level == "Low":
            # 即使是低风险用户也记录日志
            self._schedule_save(
                background_save, user_id, churn_prob, risk_level, None, start_time
            )
            return result
            
        result["recommended_action"] = "Send Retention Email"
        
        # 3. 构建 RAG 搜索查询
        country = feature_context.get('country', 'global')
        source = feature_context.get('traffic_source', 'general')
        spend = feature_context.get('monetary_90d', 0)
        
        search_query_text = f"Customer from {country} via {source} spending {spend}"
        
        # 4. 获取嵌入向量并搜索相似策略
        query_vector = self.llm_service.get_text_embedding(search_query_text)
        policies = self.bq_service.search_similar_policies(query_vector, top_k=3)
        
        result["retention_policies"] = policies
        
        # 5. 使用 Gemini 生成挽留邮件
        email_content = self.llm_service.generate_retention_email(profile, policies)
        result["generated_email"] = email_content
        
        # 6. 调度后台保存任务 (非阻塞)
        self._schedule_save(
            background_save, user_id, churn_prob, risk_level, email_content, start_time
        )
        
        return result
    
    def _schedule_save(
        self,
        background_save: Optional[Callable],
        user_id: str,
        churn_prob: float,
        risk_level: str,
        email_content: Optional[str],
        start_time: float
    ):
        """
        调度后台保存任务
        
        如果提供了 background_save 回调，则使用 FastAPI BackgroundTasks 异步保存；
        否则直接同步保存 (用于测试或非 HTTP 上下文)
        """
        # 计算处理耗时
        processing_time_ms = (time.time() - start_time) * 1000
        
        if background_save:
            # 使用 BackgroundTasks 异步保存 (不阻塞响应)
            background_save(
                storage_service.save_analysis_result,
                user_id=user_id,
                churn_probability=churn_prob,
                risk_level=risk_level,
                generated_email=email_content,
                processing_time_ms=processing_time_ms
            )
            print(f"[Orchestrator] 已调度后台保存任务: user_id={user_id}")
        else:
            # 同步保存 (fallback)
            try:
                storage_service.save_analysis_result(
                    user_id=user_id,
                    churn_probability=churn_prob,
                    risk_level=risk_level,
                    generated_email=email_content,
                    processing_time_ms=processing_time_ms
                )
            except Exception as e:
                # 存储失败不应影响主流程
                print(f"[Orchestrator] 存储失败 (非阻塞): {e}")
