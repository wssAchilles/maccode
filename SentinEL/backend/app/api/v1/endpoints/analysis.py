"""
SentinEL 分析 API 端点
提供用户流失风险分析和挽留策略生成接口
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from app.models.schemas import UserAnalysisRequest, UserAnalysisResponse, FeedbackRequest
from app.services.orchestrator import AnalysisOrchestrator
from app.services.storage_service import StorageService
from app.core.security import verify_api_key

router = APIRouter(dependencies=[Depends(verify_api_key)])
orchestrator = AnalysisOrchestrator()


@router.post("/analyze", response_model=UserAnalysisResponse)
def analyze_user_endpoint(
    request: UserAnalysisRequest,
    background_tasks: BackgroundTasks
):
    """
    **分析用户流失风险并生成干预策略**
    
    工作流程:
    1. 从 BigQuery ML 获取用户流失预测
    2. 若为高风险用户，执行 RAG 检索相关挽留策略
    3. 使用 Gemini 2.5 Pro 生成个性化挽留邮件
    4. **后台异步**将分析结果持久化到 Firestore
    
    响应说明:
    - **Low Risk**: 仅返回风险画像
    - **High Risk**: 返回完整的 RAG 策略和生成的邮件
    
    注意: Firestore 存储在后台执行，不影响 API 响应速度
    """
    try:
        # 调用编排器，传入 BackgroundTasks.add_task 作为回调
        result = orchestrator.analyze_user_workflow(
            user_id=request.user_id,
            background_save=background_tasks.add_task
        )
        return UserAnalysisResponse(**result)
    
    except Exception as e:
        # 检查是否为 404 错误 (如用户不存在)
        if hasattr(e, "status_code") and e.status_code == 404:
            raise HTTPException(status_code=404, detail=str(e))
        
        # 记录错误日志 (生产环境应使用结构化日志)
        print(f"[AnalysisEndpoint] Error: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=500,
            detail="分析过程中发生内部错误，请稍后重试"
        )


@router.post("/feedback")
def submit_feedback(request: FeedbackRequest):
    """
    **提交用户反馈**
    
    用于人工评估 AI 生成的邮件质量 (Thumbs Up/Down)
    """
    from app.services.storage_service import storage_service
    
    success = storage_service.update_feedback(
        analysis_id=request.analysis_id,
        feedback_type=request.feedback_type
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save feedback")
    
    return {"status": "success", "message": "Feedback received"}
