"""
SentinEL 推荐 API 端点
提供个性化挽留策略推荐接口
"""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.services.recommendation_service import get_recommendation_service, RecommendationService
from app.services.storage_service import get_storage_service
from app.core.security import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(verify_api_key)])


class RecommendationResponse(BaseModel):
    id: str
    type: str
    description: str
    score: float


@router.get("/recommendations/{user_id}", response_model=List[RecommendationResponse])
async def get_user_recommendations(
    user_id: str,
    top_k: int = 3,
    storage = Depends(get_storage_service)
):
    """
    获取指定用户的智能挽留策略推荐
    
    1. 获取用户当前风险分数 (从最近一次分析或实时计算)
    2. 调用双塔模型 + Vector Search 获取推荐策略
    """
    rec_service = get_recommendation_service()
    if not rec_service:
        raise HTTPException(status_code=503, detail="Recommendation service unavailable")
        
    # 1. 获取用户风险分数
    # 这里我们尝试从最近的分析记录中获取，如果找不到，默认设为 0.5 (中等风险)
    # 实际上应该有更完善的 User Profile Service
    try:
        profile = storage.get_user_profile(user_id)
        if profile and "churn_probability" in profile:
            risk_score = profile["churn_probability"]
        else:
            # 尝试查最近的分析记录
            logs = storage.get_recent_analysis_logs(user_id, limit=1)
            if logs:
                risk_score = logs[0].get("churn_probability", 0.5)
            else:
                risk_score = 0.5 # 冷启动默认值
                
        logger.info(f"Getting recommendations for {user_id}, risk_score={risk_score}")
        
    except Exception as e:
        logger.warning(f"Failed to fetch user profile, using default risk: {e}")
        risk_score = 0.5

    # 2. 获取推荐
    try:
        strategies = await rec_service.get_recommendations(user_id, risk_score, top_k)
        
        # 转换格式
        response = []
        for s in strategies:
            response.append(RecommendationResponse(
                id=s["id"],
                type=s["type"],
                description=s["description"],
                score=s.get("score", 0.0)
            ))
            
        return response
        
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate recommendations")
