"""
SentinEL 内部事件处理端点
用于接收 Pub/Sub Push 回调 (无 API Key 验证，由 Cloud Run IAM 保护)
"""

import json
import base64
import logging
from fastapi import APIRouter, HTTPException, Request
from app.services.orchestrator import AnalysisOrchestrator
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

# 注意: 此 router 不包含 API Key 验证
# 安全性由以下机制保障:
# 1. Cloud Run IAM: 仅授予 Pub/Sub 服务账号 run.invoker 权限
# 2. Pub/Sub OIDC Token: 配置时启用了 push-auth-service-account
router = APIRouter()
orchestrator = AnalysisOrchestrator()
storage_service = StorageService()


@router.post("/process")
async def process_pubsub_event(request: Request):
    """
    **Pub/Sub Push 回调端点 (内部使用)**
    
    接收 Pub/Sub 推送的消息，执行实际的 AI 分析任务。
    
    消息格式 (Pub/Sub Push):
    {
        "message": {
            "data": "<base64-encoded-json>",
            "messageId": "...",
            "publishTime": "..."
        },
        "subscription": "..."
    }
    
    Returns:
        dict: 处理状态
    """
    try:
        # 1. 解析 Pub/Sub 推送消息
        envelope = await request.json()
        
        if not envelope or "message" not in envelope:
            logger.warning("[EventsProcess] Invalid Pub/Sub message format")
            return {"status": "error", "message": "Invalid message format"}
        
        # 2. 解码 Base64 消息数据
        pubsub_message = envelope["message"]
        message_data_b64 = pubsub_message.get("data", "")
        
        if not message_data_b64:
            logger.warning("[EventsProcess] Empty message data")
            return {"status": "error", "message": "Empty message data"}
        
        message_data = json.loads(base64.b64decode(message_data_b64).decode("utf-8"))
        
        user_id = message_data.get("user_id")
        analysis_id = message_data.get("analysis_id")
        image_data = message_data.get("image_data")  # 可选
        
        if not user_id or not analysis_id:
            logger.error("[EventsProcess] Missing required fields in message")
            return {"status": "error", "message": "Missing user_id or analysis_id"}
        
        logger.info(f"[EventsProcess] Processing analysis {analysis_id} for user {user_id}")
        
        # 3. 更新状态为 PROCESSING
        storage_service.update_status(analysis_id, "PROCESSING")
        
        # 4. 执行 AI 分析工作流
        try:
            result = orchestrator.analyze_user_workflow(
                user_id=user_id,
                analysis_id=analysis_id,
                image_data=image_data,
                is_async_worker=True  # 标记为异步 Worker 模式
            )
            
            # 5. 更新状态为 COMPLETED，并保存结果 (包含 A/B 实验字段和策略)
            storage_service.update_status(
                analysis_id,
                "COMPLETED",
                risk_level=result.get("risk_level"),
                churn_probability=result.get("churn_probability"),
                retention_policies=result.get("retention_policies", []),
                generated_email=result.get("generated_email"),
                call_script=result.get("call_script"),
                processing_time_ms=result.get("processing_time_ms"),
                experiment_group=result.get("experiment_group"),
                model_used=result.get("model_used")
            )
            
            logger.info(f"[EventsProcess] Analysis {analysis_id} completed successfully")
            return {"status": "success", "analysis_id": analysis_id}
            
        except Exception as workflow_error:
            # 6. 工作流失败，标记为 FAILED
            logger.error(f"[EventsProcess] Workflow failed for {analysis_id}: {workflow_error}")
            storage_service.update_status(
                analysis_id,
                "FAILED",
                error_message=str(workflow_error)
            )
            # 返回 200 以确认消息（避免无限重试），但记录错误
            return {"status": "failed", "analysis_id": analysis_id, "error": str(workflow_error)}
    
    except Exception as e:
        logger.error(f"[EventsProcess] Unexpected error: {e}")
        # 返回 500 让 Pub/Sub 重试
        raise HTTPException(status_code=500, detail=str(e))
