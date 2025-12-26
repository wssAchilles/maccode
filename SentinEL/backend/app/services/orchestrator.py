"""
SentinEL 业务编排器
协调 BigQuery, LLM 和 Storage 服务完成用户分析流程
"""

import time
from typing import Optional, Callable
from app.services.bigquery_service import BigQueryService
from app.services.llm_service import LLMService
from app.services.storage_service import get_storage_service
from app.services.judge_service import AIJudge
from app.core import telemetry
# from opentelemetry import trace
import logging
import asyncio
from fastapi import BackgroundTasks
import base64
from app.services.tts_service import TTSService
from app.core.cache import cached_analysis
from app.services.experiment_service import experiment_service
from app.services.feature_store_service import get_feature_store_service

logger = logging.getLogger(__name__)
tracer = telemetry.get_tracer()


class AnalysisOrchestrator:
    """
    分析编排器
    负责协调各个服务完成完整的用户分析和挽留流程
    """
    
    def __init__(self):
        self.bq_service = BigQueryService()
        self.llm_service = LLMService()
        self.storage_service = get_storage_service()  # Initialize StorageService safely
        self.judge_service = AIJudge() # Initialize AIJudge
        self.tts_service = TTSService() # Initialize TTSService

    @cached_analysis(ttl_seconds=3600)  # 缓存 1 小时
    def analyze_user_workflow(
        self,
        user_id: str,
        analysis_id: Optional[str] = None,
        image_data: Optional[str] = None,  # Base64 image
        background_save: Optional[Callable] = None,
        is_async_worker: bool = False
    ) -> dict:
        """
        编排完整的用户分析和挽留工作流 (Multimodal)
        
        Args:
            user_id: 目标用户 ID
            analysis_id: 可选的预生成分析 ID (异步模式必须提供)
            image_data: Base64 编码的图片数据 (竞争对手优惠/截图)
            background_save: 可选的后台保存回调函数
            is_async_worker: 是否为异步 Worker 模式 (跳过 ID 生成和后台保存)
        """
        # 记录开始时间
        logger.info(f"SentinEL-Orchestrator: STARTING ANALYSIS for user {user_id}")
        start_time = time.time()
        
        # 0. 获取或生成分析 ID
        # 0. 获取或生成分析 ID
        if not analysis_id and self.storage_service:
            analysis_id = self.storage_service.generate_id()
        elif not analysis_id:
            # Fallback if storage service failed
            import uuid
            analysis_id = str(uuid.uuid4())
        
        # A/B 测试: 获取实验分组和模型
        experiment_group, model_name = experiment_service.get_model_for_user(user_id)

        # 1. BigQuery: 获取画像
        profile = self.bq_service.get_user_churn_prediction(user_id)
        churn_prob = profile.get("churn_probability", 0.0)
        risk_level = "High" if profile.get("predicted_label") == 1 else "Low"
        
        feature_context = profile.get("features", {})
        
        # 1.5 Feature Store: 获取实时特征 (Real-time Context)
        try:
            fs_service = get_feature_store_service()
            if fs_service:
                realtime_features = fs_service.get_online_features(user_id)
                if realtime_features:
                    logger.info(f"Retrieved realtime features for {user_id}: {realtime_features}")
                    # 合并到特征上下文，覆盖同名离线特征
                    feature_context.update(realtime_features)
                    # 也可以单独存一个字段
                    result["realtime_features"] = realtime_features
        except Exception as e:
            logger.warning(f"Feature Store retrieval failed: {e}")
        
        # 默认结果
        result = {
            "user_id": user_id,
            "risk_level": risk_level,
            "churn_probability": churn_prob,
            "user_features": feature_context,
            "retention_policies": [],
            "generated_email": None,
            "call_script": None,
            "generated_audio": None,
            "recommended_action": "No intervention needed",
            "analysis_id": analysis_id,
            "experiment_group": experiment_group,
            "model_used": model_name
        }

        # 2. 低风险跳过 (除非强制，暂简单处理)
        if risk_level == "Low":
            self._schedule_save(
                 background_save, user_id, churn_prob, risk_level, None, start_time, analysis_id
            )
            return result
            
        result["recommended_action"] = "Send Retention Email"
        
        # 3. RAG 搜索
        country = feature_context.get('country', 'global')
        source = feature_context.get('traffic_source', 'general')
        spend = feature_context.get('monetary_90d', 0)
        search_query_text = f"Customer from {country} via {source} spending {spend}"
        
        query_vector = self.llm_service.get_text_embedding(search_query_text)
        policies = self.bq_service.search_similar_policies(query_vector, top_k=3)
        result["retention_policies"] = policies
        
        # 4. Vision & LLM: 生成邮件
        # Decode image if present
        image_bytes = None
        if image_data:
            try:
                # Remove header if present (e.g. "data:image/jpeg;base64,")
                if "," in image_data:
                    image_data = image_data.split(",")[1]
                image_bytes = base64.b64decode(image_data)
                logger.info("Image decoded successfully for vision analysis.")
            except Exception as e:
                logger.error(f"Failed to decode image: {e}")

        email_content = self.llm_service.generate_retention_email(profile, policies, image_bytes, model_name)
        result["generated_email"] = email_content
        
        # 5. 生成通话脚本 & TTS 语音 (串行执行，确保内容一致性)
        if email_content:
            # A. Generate Script
            call_script = self.llm_service.generate_call_script(email_content)
            result["call_script"] = call_script
            
            # B. Synthesize Audio
            audio_base64 = self.tts_service.generate_voicemail_audio(call_script)
            result["generated_audio"] = audio_base64

        # 6. 计算处理时间
        end_time = time.time()
        processing_time_ms = int((end_time - start_time) * 1000)
        result["processing_time_ms"] = processing_time_ms

        # 7. 后台保存 (仅同步模式)
        if not is_async_worker:
            self._schedule_save(
                background_save, user_id, churn_prob, risk_level, email_content, start_time, analysis_id
            )

        if email_content and background_save and not is_async_worker:
             background_save(
                self._run_audit_task,
                user_profile=profile,
                generated_email=email_content,
                applied_policies=policies,
                analysis_id=analysis_id
            )
        
        return result

    def _schedule_save(self, background_save, user_id: str, churn_prob: float, risk_level: str, generated_email: str, start_time: float, analysis_id: str):
        """Helper to run storage save in background"""
        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)
        
        if background_save and self.storage_service:
             background_save(
                 self.storage_service.save_analysis_result,
                 user_id=user_id,
                 churn_probability=churn_prob,
                 risk_level=risk_level,
                 generated_email=generated_email,
                 processing_time_ms=latency_ms,
                 analysis_id=analysis_id
             )
        elif self.storage_service:
             # Fallback if no background_save provided (e.g. testing)
             self.storage_service.save_analysis_result(
                 user_id=user_id,
                 churn_probability=churn_prob,
                 risk_level=risk_level,
                 generated_email=generated_email,
                 processing_time_ms=latency_ms,
                 analysis_id=analysis_id
             )

    def _run_audit_task(self, user_profile: dict, generated_email: str, applied_policies: list, analysis_id: str):
        """
        Background task to run AI Audit (Judge) and update Firestore.
        """
        with tracer.start_as_current_span("run_audit_task"):
            try:
                # 1. Run Evaluation
                audit_result = self.judge_service.evaluate_response(
                    user_profile=user_profile,
                    generated_email=generated_email,
                    applied_policies=applied_policies
                )
                
                # 2. Update Firestore
                if self.storage_service:
                    self.storage_service.update_audit_result(analysis_id, audit_result)
                
            except Exception as e:
                logger.error(f"Background audit failed for {analysis_id}: {e}")


# 单例实例
_orchestrator_instance = None

def get_orchestrator() -> "AnalysisOrchestrator":
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = AnalysisOrchestrator()
    return _orchestrator_instance
