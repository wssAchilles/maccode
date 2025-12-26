"""
SentinEL 分析 API 端点
提供用户流失风险分析和挽留策略生成接口
支持异步 Pub/Sub 消息队列处理模式
"""

import json
import base64
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Request
from pydantic import BaseModel
from app.models.schemas import UserAnalysisRequest, UserAnalysisResponse, FeedbackRequest
from app.services.orchestrator import AnalysisOrchestrator
from app.services.storage_service import StorageService
from app.services.queue_service import queue_service
from app.core.security import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(verify_api_key)])
orchestrator = AnalysisOrchestrator()
storage_service = StorageService()


# ==============================================================================
# 异步分析响应模型
# ==============================================================================
class AsyncAnalysisResponse(BaseModel):
    """异步分析请求响应"""
    analysis_id: str
    status: str = "QUEUED"
    message: str = "分析任务已加入队列"


# ==============================================================================
# 面向前端的端点
# ==============================================================================
@router.post("/analyze", response_model=AsyncAnalysisResponse, status_code=202)
def analyze_user_endpoint(request: UserAnalysisRequest):
    """
    **异步分析用户流失风险并生成干预策略**
    
    工作流程 (Event-Driven):
    1. 在 Firestore 创建初始记录 (status: QUEUED)
    2. 发布消息到 Pub/Sub Topic
    3. **立即返回 HTTP 202 Accepted** (无需等待 AI 处理)
    4. 前端通过 Firestore 实时监听获取结果
    
    Returns:
        AsyncAnalysisResponse: 包含 analysis_id 用于追踪任务状态
    """
    try:
        # 1. 生成分析 ID
        analysis_id = storage_service.generate_id()
        
        # 2. 创建初始 Firestore 记录 (QUEUED)
        storage_service.create_queued_analysis(
            user_id=request.user_id,
            analysis_id=analysis_id
        )
        
        # 3. 发布消息到 Pub/Sub
        queue_service.publish_analysis_event(
            user_id=request.user_id,
            analysis_id=analysis_id,
            image_data=request.image_data
        )
        
        # 4. 立即返回 202 (任务已排队)
        return AsyncAnalysisResponse(
            analysis_id=analysis_id,
            status="QUEUED",
            message=f"分析任务 {analysis_id} 已加入队列"
        )
    
    except Exception as e:
        logger.error(f"[AnalysisEndpoint] Error queuing analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail="任务入队失败，请稍后重试"
        )


@router.get("/analyze/{analysis_id}")
def get_analysis_status(analysis_id: str):
    """
    **获取分析任务状态和结果**
    
    前端通过此端点轮询获取异步分析结果。
    
    Returns:
        dict: 包含 status 和完整分析结果 (当 status=COMPLETED 时)
    """
    try:
        from google.cloud import firestore
        db = firestore.Client()
        
        doc_ref = db.collection("analysis_logs").document(analysis_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")
        
        data = doc.to_dict()
        return data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AnalysisEndpoint] Error fetching analysis {analysis_id}: {e}")
        raise HTTPException(status_code=500, detail="获取分析状态失败")


# ==============================================================================
# /events/process 已移至 events.py (无 API Key 验证)
# ==============================================================================


# ==============================================================================
# 反馈端点 (保持不变)
# ==============================================================================
@router.post("/feedback")
def submit_feedback(request: FeedbackRequest):
    """
    **提交用户反馈**
    
    用于人工评估 AI 生成的邮件质量 (Thumbs Up/Down)
    """
    from app.services.storage_service import storage_service as ss
    
    success = ss.update_feedback(
        analysis_id=request.analysis_id,
        feedback_type=request.feedback_type
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save feedback")
    
    return {"status": "success", "message": "Feedback received"}
