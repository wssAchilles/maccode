"""
SentinEL 业务编排器
协调 BigQuery, LLM, Storage, Agent 和 Judge 服务完成用户分析流程

核心流程:
1. 获取用户画像和特征
2. 深度模型预测流失概率
3. Agent 生成挝留策略
4. Judge 评估策略质量 (不合格则重试)
5. 存储并返回结果
"""

import time
import asyncio
import base64
import logging
from typing import Optional, Callable, List, Dict, Any

from fastapi import BackgroundTasks

from app.services.bigquery_service import BigQueryService
from app.services.llm_service import LLMService
from app.services.storage_service import get_storage_service
from app.services.judge_service import AIJudge, get_judge_service, EvaluationResult
from app.services.tts_service import TTSService
from app.services.experiment_service import experiment_service
from app.services.feature_store_service import get_feature_store_service
from app.services.prediction_service import get_prediction_service
from app.services.recommendation_service import get_recommendation_service
from app.agents.sentinel_agent import invoke_agent
from app.core import telemetry
from app.core.cache import cached_analysis

logger = logging.getLogger(__name__)
tracer = telemetry.get_tracer()

# Judge 重试配置
MAX_JUDGE_RETRIES = 2
JUDGE_PASS_THRESHOLD = 75


class AnalysisOrchestrator:
    """
    分析编排器
    负责协调各个服务完成完整的用户分析和挽留流程
    """
    
    def __init__(self):
        self.bq_service = BigQueryService()
        self.llm_service = LLMService()
        self.storage_service = get_storage_service()  # Initialize StorageService safely
        self.judge_service = get_judge_service()  # 使用单例获取方式
        self.tts_service = TTSService() # Initialize TTSService
        self.prediction_service = get_prediction_service()  # 深度模型预测服务
        self.recommendation_service = get_recommendation_service() # 推荐服务

    @cached_analysis(ttl_seconds=3600)  # 缓存 1 小时
    async def analyze_user_workflow(
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
        if not analysis_id and self.storage_service:
            analysis_id = self.storage_service.generate_id()
        elif not analysis_id:
            # Fallback if storage service failed
            import uuid
            analysis_id = str(uuid.uuid4())
        
        # A/B 测试: 获取实验分组和模型
        experiment_group, model_name = experiment_service.get_model_for_user(user_id)

        # 1. BigQuery: 获取用户画像和特征上下文 (Sync call, lightweight enough or wrap if needed)
        # Running in main thread is okay for BigQuery simple client usually, but better to thread it if heavy
        profile = self.bq_service.get_user_churn_prediction(user_id)
        feature_context = profile.get("features", {})
        
        # 1.5 Feature Store: 获取实时特征 (Real-time Context)
        realtime_features = {}
        recent_events = []  # 用于深度模型的事件序列
        try:
            fs_service = get_feature_store_service()
            if fs_service:
                realtime_features = fs_service.get_online_features(user_id)
                if realtime_features:
                    logger.info(f"Retrieved realtime features for {user_id}: {realtime_features}")
                    feature_context.update(realtime_features)
                    # 提取事件序列用于深度模型 (如果 Feature Store 提供)
                    recent_events = realtime_features.get("recent_events", [])
        except Exception as e:
            logger.warning(f"Feature Store retrieval failed: {e}")
        
        # 2. 深度模型预测: 使用 LSTM/Transformer 预测流失概率
        # 优先使用深度模型，如果不可用则回退到 BigQuery ML
        churn_prob = profile.get("churn_probability", 0.0)  # 默认回退值
        prediction_source = "bigquery_ml"  # 记录预测来源
        
        # [STEP] 预测开始 - 实时更新 Firestore
        if self.storage_service:
            self.storage_service.update_step(
                analysis_id, "Churn Prediction", "running",
                details="调用深度模型预测流失概率..."
            )
        
        if self.prediction_service and recent_events:
            try:
                # 调用 Vertex AI Endpoint 进行深度模型预测
                deep_churn_prob = self.prediction_service.predict_churn(
                    user_id=user_id,
                    events=recent_events,
                    use_cache=True
                )
                churn_prob = deep_churn_prob
                prediction_source = "deep_lstm"
                logger.info(f"Deep model prediction for {user_id}: {churn_prob:.4f}")
                
                # 获取风险因素分析
                risk_factors = self.prediction_service.analyze_sequence_risk_factors(recent_events)
                feature_context["risk_factors"] = risk_factors
            except Exception as e:
                logger.warning(f"Deep model prediction failed, using BQ fallback: {e}")
        elif self.prediction_service and not recent_events:
            # 如果没有事件序列，尝试从 BigQuery 获取
            logger.info(f"No recent events for {user_id}, using BQ fallback")
        
        # 确定风险等级
        if self.prediction_service:
            risk_level = self.prediction_service.get_risk_level(churn_prob)
        else:
            risk_level = "High" if profile.get("predicted_label") == 1 else "Low"
        
        # [STEP] 预测完成 - 更新 Firestore 包含风险分数
        if self.storage_service:
            self.storage_service.update_step(
                analysis_id, "Churn Prediction", "completed",
                details=f"Risk: {risk_level} ({churn_prob:.2%})"
            )
            # 还要单独更新 risk_score 以触发前端 RiskGauge 动画
            self.storage_service.update_risk_score(analysis_id, churn_prob, risk_level)
        
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
            "model_used": model_name,
            "recommended_strategies": [] # 新增字段
        }

        # 2. 低风险跳过 (除非强制，暂简单处理)
        if risk_level == "Low":
            self._schedule_save(
                 background_save, user_id, churn_prob, risk_level, None, start_time, analysis_id
            )
            return result
        
        # 2.5 智能策略推荐 (双塔模型 + Vector Search) (ASYNC)
        if self.recommendation_service:
            try:
                strategies = await self.recommendation_service.get_recommendations(user_id, churn_prob)
                result["recommended_strategies"] = strategies
                logger.info(f"生成 {len(strategies)} 个推荐策略")
            except Exception as e:
                logger.error(f"策略推荐失败: {e}", exc_info=True)
            
        result["recommended_action"] = "Send Retention Email"
        
        # =============================================================
        # 3. Agent + Judge 循环: 生成-评估-修正 (Agentic Reflection)
        # =============================================================
        strategy_text = None
        agent_trace_log = []
        judge_history = []  # 记录 Judge 评估历史
        feedback = None  # 初始无反馈
        
        current_loop = asyncio.get_running_loop()

        for attempt in range(MAX_JUDGE_RETRIES + 1):
            try:
                # 3.1 调用 Agent 生成策略 (ASYNC)
                logger.info(f"[Agent] Attempt {attempt + 1}/{MAX_JUDGE_RETRIES + 1} | user={user_id} | feedback={feedback is not None}")
                
                # [STEP] Agent 生成策略 - 更新状态
                step_name = "Drafting Strategy" if attempt == 0 else "Refining Strategy"
                if self.storage_service:
                    self.storage_service.update_step(
                        analysis_id, step_name, "running",
                        details=f"Attempt {attempt + 1}/{MAX_JUDGE_RETRIES + 1}",
                        has_feedback=feedback is not None
                    )
                
                # Direct AWAIT call, no manual event loop
                agent_result = await invoke_agent(user_id=user_id, feedback=feedback)
                
                strategy_text = agent_result.get("final_result", "")
                agent_trace_log = agent_result.get("trace_log", [])
                
                if not strategy_text:
                    logger.warning("[Agent] 未能生成策略文本")
                    break
                
                # 3.2 Judge 评估策略 (SYNC -> Wrap in Thread)
                logger.info(f"[Judge] 开始评估策略 (Attempt {attempt + 1})")
                
                # [STEP] Judge 审核开始
                if self.storage_service:
                    self.storage_service.update_step(
                        analysis_id, "AI Judge Review", "running",
                        details="评估共情度/清晰度/风险匹配度..."
                    )
                
                # 获取用户标签以便 Judge 更好的评估
                user_tags = feature_context.get("user_segment", "")
                if churn_prob > 0.8:
                    user_tags += " VIP高风险"
                
                # Use run_in_executor for synchronous Judge call
                evaluation = await current_loop.run_in_executor(
                    None,
                    lambda: self.judge_service.evaluate_strategy(
                        strategy_text=strategy_text,
                        user_risk_level=risk_level,
                        user_tags=user_tags or None
                    )
                )
                
                # 记录评估历史
                judge_history.append({
                    "attempt": attempt + 1,
                    "score": evaluation.score,
                    "verdict": evaluation.verdict,
                    "reason": evaluation.reason,
                    "suggestions": evaluation.suggestions
                })
                
                logger.info(
                    f"[Judge] Attempt {attempt + 1} | Score: {evaluation.score} | "
                    f"Verdict: {evaluation.verdict} | Feedback: {evaluation.suggestions[:80]}..."
                )
                
                # 3.3 判定是否通过 + 更新 Firestore
                if evaluation.verdict == "PASS":
                    logger.info(f"[Judge] 策略通过审核 (Score: {evaluation.score})")
                    # [STEP] Judge PASS
                    if self.storage_service:
                        self.storage_service.update_step(
                            analysis_id, "AI Judge Review", "completed",
                            score=evaluation.score,
                            verdict="PASS",
                            details="策略已通过质量审核"
                        )
                    break
                else:
                    # [STEP] Judge FAIL - 显示反馈
                    if self.storage_service:
                        self.storage_service.update_step(
                            analysis_id, "AI Judge Review", "warning" if attempt < MAX_JUDGE_RETRIES else "error",
                            score=evaluation.score,
                            verdict="FAIL",
                            feedback=evaluation.suggestions,
                            details=f"Score: {evaluation.score} - {evaluation.reason[:50]}"
                        )
                
                # 未通过，准备反馈给 Agent 重试
                if attempt < MAX_JUDGE_RETRIES:
                    feedback = (
                        f"你上一次生成的策略被 Judge 评分为 {evaluation.score} 分，未能通过 (< 75)\u3002\n"
                        f"评估理由: {evaluation.reason}\n"
                        f"改进建议: {evaluation.suggestions}\n\n"
                        f"请根据以上反馈，重新撰写一个更高质量的挝留策略。"
                    )
                    logger.info(f"[Judge] 准备重试，将反馈传递给 Agent")
                else:
                    logger.warning(f"[Judge] 达到最大重试次数，使用当前策略")
                    
            except Exception as e:
                logger.error(f"[Agent/Judge] 循环失败: {e}", exc_info=True)
                break
        
        # 将 Agent 生成的策略和 Judge 历史记录到结果中
        result["generated_strategy"] = strategy_text
        result["agent_trace_log"] = agent_trace_log
        result["judge_history"] = judge_history
            
        # 4. RAG 搜索 & 邮件生成 (LLM Service calls usually sync, wrap or accept blocking)
        # Assuming LLMService is sync for now, keeping it simple or wrapping if too slow
        country = feature_context.get('country', 'global')
        source = feature_context.get('traffic_source', 'general')
        spend = feature_context.get('monetary_90d', 0)
        search_query_text = f"Customer from {country} via {source} spending {spend}"
        
        # 简单处理 RAG 部分的同步调用
        policies = await current_loop.run_in_executor(
            None,
            lambda: self.bq_service.search_similar_policies(
                self.llm_service.get_text_embedding(search_query_text), 
                top_k=3
            )
        )
        result["retention_policies"] = policies
        
        # 5. Vision & LLM: 生成邮件 (Sync)
        image_bytes = None
        if image_data:
            try:
                if "," in image_data:
                    image_data = image_data.split(",")[1]
                image_bytes = base64.b64decode(image_data)
                logger.info("图片解码成功")
            except Exception as e:
                logger.error(f"图片解码失败: {e}")

        email_content = await current_loop.run_in_executor(
            None,
            lambda: self.llm_service.generate_retention_email(profile, policies, image_bytes, model_name)
        )
        result["generated_email"] = email_content
        
        # 6. 生成通话脚本 & TTS 语音 (Sync)
        if email_content:
            call_script = await current_loop.run_in_executor(
                None,
                lambda: self.llm_service.generate_call_script(email_content)
            )
            result["call_script"] = call_script
            
            audio_base64 = await current_loop.run_in_executor(
                None,
                lambda: self.tts_service.generate_voicemail_audio(call_script)
            )
            result["generated_audio"] = audio_base64

        # 7. 计算处理时间
        end_time = time.time()
        processing_time_ms = int((end_time - start_time) * 1000)
        result["processing_time_ms"] = processing_time_ms

        # 8. 后台保存 (仅同步模式)
        if not is_async_worker:
            self._schedule_save(
                background_save, user_id, churn_prob, risk_level, email_content, start_time, analysis_id
            )

        # Judge 审计任务 (异步) - 这里依然通过 background_save 提交，但 task 本身是 sync 的
        # 如果 is_async_worker=True (PubSub), 调用方负责保存, 这里 result 包含了所有数据
        
        return result
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

        # 1. BigQuery: 获取用户画像和特征上下文
        profile = self.bq_service.get_user_churn_prediction(user_id)
        feature_context = profile.get("features", {})
        
        # 1.5 Feature Store: 获取实时特征 (Real-time Context)
        realtime_features = {}
        recent_events = []  # 用于深度模型的事件序列
        try:
            fs_service = get_feature_store_service()
            if fs_service:
                realtime_features = fs_service.get_online_features(user_id)
                if realtime_features:
                    logger.info(f"Retrieved realtime features for {user_id}: {realtime_features}")
                    feature_context.update(realtime_features)
                    # 提取事件序列用于深度模型 (如果 Feature Store 提供)
                    recent_events = realtime_features.get("recent_events", [])
        except Exception as e:
            logger.warning(f"Feature Store retrieval failed: {e}")
        
        # 2. 深度模型预测: 使用 LSTM/Transformer 预测流失概率
        # 优先使用深度模型，如果不可用则回退到 BigQuery ML
        churn_prob = profile.get("churn_probability", 0.0)  # 默认回退值
        prediction_source = "bigquery_ml"  # 记录预测来源
        
        # [STEP] 预测开始 - 实时更新 Firestore
        if self.storage_service:
            self.storage_service.update_step(
                analysis_id, "Churn Prediction", "running",
                details="调用深度模型预测流失概率..."
            )
        
        if self.prediction_service and recent_events:
            try:
                # 调用 Vertex AI Endpoint 进行深度模型预测
                deep_churn_prob = self.prediction_service.predict_churn(
                    user_id=user_id,
                    events=recent_events,
                    use_cache=True
                )
                churn_prob = deep_churn_prob
                prediction_source = "deep_lstm"
                logger.info(f"Deep model prediction for {user_id}: {churn_prob:.4f}")
                
                # 获取风险因素分析
                risk_factors = self.prediction_service.analyze_sequence_risk_factors(recent_events)
                feature_context["risk_factors"] = risk_factors
            except Exception as e:
                logger.warning(f"Deep model prediction failed, using BQ fallback: {e}")
        elif self.prediction_service and not recent_events:
            # 如果没有事件序列，尝试从 BigQuery 获取
            logger.info(f"No recent events for {user_id}, using BQ fallback")
        
        # 确定风险等级
        if self.prediction_service:
            risk_level = self.prediction_service.get_risk_level(churn_prob)
        else:
            risk_level = "High" if profile.get("predicted_label") == 1 else "Low"
        
        # [STEP] 预测完成 - 更新 Firestore 包含风险分数
        if self.storage_service:
            self.storage_service.update_step(
                analysis_id, "Churn Prediction", "completed",
                details=f"Risk: {risk_level} ({churn_prob:.2%})"
            )
            # 还要单独更新 risk_score 以触发前端 RiskGauge 动画
            self.storage_service.update_risk_score(analysis_id, churn_prob, risk_level)
        
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

            "model_used": model_name,
            "recommended_strategies": [] # 新增字段
        }

        # 2. 低风险跳过 (除非强制，暂简单处理)
        if risk_level == "Low":
            self._schedule_save(
                 background_save, user_id, churn_prob, risk_level, None, start_time, analysis_id
            )
            return result
        
        # 2.5 智能策略推荐 (双塔模型 + Vector Search)
        if self.recommendation_service:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                strategies = loop.run_until_complete(
                    self.recommendation_service.get_recommendations(user_id, churn_prob)
                )
                loop.close()
                result["recommended_strategies"] = strategies
                logger.info(f"生成 {len(strategies)} 个推荐策略")
            except Exception as e:
                logger.error(f"策略推荐失败: {e}")
            
        result["recommended_action"] = "Send Retention Email"
        
        # =============================================================
        # 3. Agent + Judge 循环: 生成-评估-修正 (Agentic Reflection)
        # =============================================================
        strategy_text = None
        agent_trace_log = []
        judge_history = []  # 记录 Judge 评估历史
        feedback = None  # 初始无反馈
        
        for attempt in range(MAX_JUDGE_RETRIES + 1):
            try:
                # 3.1 调用 Agent 生成策略
                logger.info(f"[Agent] Attempt {attempt + 1}/{MAX_JUDGE_RETRIES + 1} | user={user_id} | feedback={feedback is not None}")
                
                # [STEP] Agent 生成策略 - 更新状态
                step_name = "Drafting Strategy" if attempt == 0 else "Refining Strategy"
                if self.storage_service:
                    self.storage_service.update_step(
                        analysis_id, step_name, "running",
                        details=f"Attempt {attempt + 1}/{MAX_JUDGE_RETRIES + 1}",
                        has_feedback=feedback is not None
                    )
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                agent_result = loop.run_until_complete(
                    invoke_agent(user_id=user_id, feedback=feedback)
                )
                loop.close()
                
                strategy_text = agent_result.get("final_result", "")
                agent_trace_log = agent_result.get("trace_log", [])
                
                if not strategy_text:
                    logger.warning("[Agent] 未能生成策略文本")
                    break
                
                # 3.2 Judge 评估策略
                logger.info(f"[Judge] 开始评估策略 (Attempt {attempt + 1})")
                
                # [STEP] Judge 审核开始
                if self.storage_service:
                    self.storage_service.update_step(
                        analysis_id, "AI Judge Review", "running",
                        details="评估共情度/清晰度/风险匹配度..."
                    )
                
                # 获取用户标签以便 Judge 更好的评估
                user_tags = feature_context.get("user_segment", "")
                if churn_prob > 0.8:
                    user_tags += " VIP高风险"
                
                evaluation = self.judge_service.evaluate_strategy(
                    strategy_text=strategy_text,
                    user_risk_level=risk_level,
                    user_tags=user_tags or None
                )
                
                # 记录评估历史
                judge_history.append({
                    "attempt": attempt + 1,
                    "score": evaluation.score,
                    "verdict": evaluation.verdict,
                    "reason": evaluation.reason,
                    "suggestions": evaluation.suggestions
                })
                
                logger.info(
                    f"[Judge] Attempt {attempt + 1} | Score: {evaluation.score} | "
                    f"Verdict: {evaluation.verdict} | Feedback: {evaluation.suggestions[:80]}..."
                )
                
                # 3.3 判定是否通过 + 更新 Firestore
                if evaluation.verdict == "PASS":
                    logger.info(f"[Judge] 策略通过审核 (Score: {evaluation.score})")
                    # [STEP] Judge PASS
                    if self.storage_service:
                        self.storage_service.update_step(
                            analysis_id, "AI Judge Review", "completed",
                            score=evaluation.score,
                            verdict="PASS",
                            details="策略已通过质量审核"
                        )
                    break
                else:
                    # [STEP] Judge FAIL - 显示反馈
                    if self.storage_service:
                        self.storage_service.update_step(
                            analysis_id, "AI Judge Review", "warning" if attempt < MAX_JUDGE_RETRIES else "error",
                            score=evaluation.score,
                            verdict="FAIL",
                            feedback=evaluation.suggestions,
                            details=f"Score: {evaluation.score} - {evaluation.reason[:50]}"
                        )
                
                # 未通过，准备反馈给 Agent 重试
                if attempt < MAX_JUDGE_RETRIES:
                    feedback = (
                        f"你上一次生成的策略被 Judge 评分为 {evaluation.score} 分，未能通过 (< 75)\u3002\n"
                        f"评估理由: {evaluation.reason}\n"
                        f"改进建议: {evaluation.suggestions}\n\n"
                        f"请根据以上反馈，重新撰写一个更高质量的挝留策略。"
                    )
                    logger.info(f"[Judge] 准备重试，将反馈传递给 Agent")
                else:
                    logger.warning(f"[Judge] 达到最大重试次数，使用当前策略")
                    
            except Exception as e:
                logger.error(f"[Agent/Judge] 循环失败: {e}")
                break
        
        # 将 Agent 生成的策略和 Judge 历史记录到结果中
        result["generated_strategy"] = strategy_text
        result["agent_trace_log"] = agent_trace_log
        result["judge_history"] = judge_history
            
        # 4. RAG 搜索 & 邮件生成
        country = feature_context.get('country', 'global')
        source = feature_context.get('traffic_source', 'general')
        spend = feature_context.get('monetary_90d', 0)
        search_query_text = f"Customer from {country} via {source} spending {spend}"
        
        query_vector = self.llm_service.get_text_embedding(search_query_text)
        policies = self.bq_service.search_similar_policies(query_vector, top_k=3)
        result["retention_policies"] = policies
        
        # 5. Vision & LLM: 生成邮件 (基于策略文本)
        image_bytes = None
        if image_data:
            try:
                if "," in image_data:
                    image_data = image_data.split(",")[1]
                image_bytes = base64.b64decode(image_data)
                logger.info("图片解码成功")
            except Exception as e:
                logger.error(f"图片解码失败: {e}")

        email_content = self.llm_service.generate_retention_email(profile, policies, image_bytes, model_name)
        result["generated_email"] = email_content
        
        # 6. 生成通话脚本 & TTS 语音
        if email_content:
            call_script = self.llm_service.generate_call_script(email_content)
            result["call_script"] = call_script
            
            audio_base64 = self.tts_service.generate_voicemail_audio(call_script)
            result["generated_audio"] = audio_base64

        # 7. 计算处理时间
        end_time = time.time()
        processing_time_ms = int((end_time - start_time) * 1000)
        result["processing_time_ms"] = processing_time_ms

        # 8. 后台保存 (仅同步模式)
        if not is_async_worker:
            self._schedule_save(
                background_save, user_id, churn_prob, risk_level, email_content, start_time, analysis_id
            )

        # Judge 审计任务 (异步)
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
