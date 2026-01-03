"""
SentinEL 分析 API 端点
提供用户流失风险分析和挽留策略生成接口
支持异步 Pub/Sub 消息队列处理模式
"""

import json
import base64
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Request, UploadFile
from pydantic import BaseModel
from app.models.schemas import UserAnalysisRequest, UserAnalysisResponse, FeedbackRequest
from app.services.orchestrator import get_orchestrator
from app.services.storage_service import get_storage_service
from app.services.queue_service import get_queue_service
from app.core.security import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(verify_api_key)])
# orchestrator initialized lazily
# storage_service initialized lazily


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
        storage_service = get_storage_service()
        if not storage_service:
            raise HTTPException(status_code=500, detail="Database service unavailable")
            
        analysis_id = storage_service.generate_id()
        
        # 2. 创建初始 Firestore 记录 (QUEUED)
        storage_service.create_queued_analysis(
            user_id=request.user_id,
            analysis_id=analysis_id
        )
        
        # 3. 发布消息到 Pub/Sub
        queue_service = get_queue_service()
        if not queue_service:
             logger.error("Queue service unavailable")
             # Consider raising error or fallback
             raise HTTPException(status_code=500, detail="Messaging service unavailable")

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
    from app.services.storage_service import get_storage_service
    
    ss = get_storage_service()
    if not ss:
        raise HTTPException(status_code=500, detail="Database service unavailable")

    success = ss.update_feedback(
        analysis_id=request.analysis_id,
        feedback_type=request.feedback_type
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save feedback")
    
    return {"status": "success", "message": "Feedback received"}


# ==============================================================================
# 竞品分析端点 (多模态视觉分析)
# ==============================================================================
class CompetitorIntelligenceResponse(BaseModel):
    """竞品分析响应"""
    competitor_name: str
    offer_price: str
    offer_details: str
    weakness: str
    analysis_id: Optional[str] = None


@router.post("/analyze-competitor", response_model=CompetitorIntelligenceResponse)
async def analyze_competitor_image(
    file: UploadFile,
    analysis_id: Optional[str] = None
):
    """
    **竞品优惠截图分析 (多模态 AI)**
    
    用户上传竞品优惠截图，使用 Gemini 2.0 Flash 进行视觉分析，
    提取关键情报供后续 Agent 挽留策略使用。
    
    Args:
        file: 图片文件 (支持 JPEG/PNG)
        analysis_id: 可选，关联到特定分析会话
    
    Returns:
        CompetitorIntelligenceResponse: 结构化竞品情报
    """
    # 验证文件类型
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="仅支持图片文件 (JPEG/PNG)"
        )
    
    try:
        # 读取图片数据
        image_bytes = await file.read()
        
        if len(image_bytes) > 10 * 1024 * 1024:  # 10MB 限制
            raise HTTPException(
                status_code=400,
                detail="图片文件过大，请上传 10MB 以内的图片"
            )
        
        logger.info(f"[AnalyzeCompetitor] Received image: {file.filename}, size: {len(image_bytes)} bytes")
        
        # 调用 LLM 视觉分析
        from app.services.llm_service import LLMService
        llm_service = LLMService()
        
        intelligence = llm_service.analyze_image(image_bytes)
        
        logger.info(f"[AnalyzeCompetitor] Analysis result: {intelligence}")
        
        # 如果提供了 analysis_id，将情报存入 Firestore
        if analysis_id:
            storage_service = get_storage_service()
            if storage_service:
                try:
                    storage_service.db.collection("analysis_logs").document(analysis_id).update({
                        "competitor_intelligence": intelligence
                    })
                    logger.info(f"[AnalyzeCompetitor] Saved intelligence to analysis {analysis_id}")
                except Exception as e:
                    logger.warning(f"[AnalyzeCompetitor] Failed to save to Firestore: {e}")
        
        return CompetitorIntelligenceResponse(
            competitor_name=intelligence.get("competitor_name", "Unknown"),
            offer_price=intelligence.get("offer_price", "N/A"),
            offer_details=intelligence.get("offer_details", ""),
            weakness=intelligence.get("weakness", ""),
            analysis_id=analysis_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AnalyzeCompetitor] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"图片分析失败: {str(e)}"
        )

