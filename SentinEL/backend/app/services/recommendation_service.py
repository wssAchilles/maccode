"""
SentinEL 推荐服务
基于双塔模型和 Vector Search 提供个性化挽留策略推荐
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from google.cloud import aiplatform
from google.protobuf import json_format
from google.cloud.aiplatform.matching_engine import matching_engine_index_endpoint

from app.core.config import settings
from app.core.telemetry import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer()

# 简单的策略缓存 (在实际生产中应从数据库加载)
# 这里为了演示，我们先硬编码一些策略映射，或者稍后从 CSV 加载
STRATEGY_MAP = {} 

class RecommendationService:
    """
    推荐服务
    
    集成 Vertex AI Prediction (User Tower) 和 Vector Search (Matching Engine)
    提供端到端的推荐能力。
    """
    
    def __init__(
        self,
        project_id: str = settings.PROJECT_ID,
        location: str = settings.LOCATION,
        user_tower_endpoint_name: str = "sentinel-user-tower-endpoint",
        vector_search_endpoint_name: str = "sentinel-strategy-index-endpoint",
        index_endpoint_id: Optional[str] = None, # 如果已知 ID 可直接传入
    ):
        self.project_id = project_id
        self.location = location
        self.user_tower_endpoint_name = user_tower_endpoint_name
        self.vector_search_endpoint_name = vector_search_endpoint_name
        
        # 客户端初始化
        aiplatform.init(project=project_id, location=location)
        
        self._user_endpoint: Optional[aiplatform.Endpoint] = None
        self._index_endpoint: Optional[aiplatform.MatchingEngineIndexEndpoint] = None
        
        # 尝试加载 ID (如果在配置中有)
        # self.index_endpoint_id = settings.VECTOR_SEARCH_ENDPOINT_ID
        
    @property
    def user_endpoint(self) -> Optional[aiplatform.Endpoint]:
        """Lazy load User Tower Endpoint"""
        if self._user_endpoint is None:
            try:
                endpoints = aiplatform.Endpoint.list(
                    filter=f'display_name="{self.user_tower_endpoint_name}"'
                )
                if endpoints:
                    self._user_endpoint = endpoints[0]
                    logger.info(f"User Tower Endpoint connected: {self._user_endpoint.resource_name}")
                else:
                    logger.warning(f"User Tower Endpoint not found: {self.user_tower_endpoint_name}")
            except Exception as e:
                logger.error(f"Failed to get User Tower Endpoint: {e}")
        return self._user_endpoint

    @property
    def index_endpoint(self) -> Optional[aiplatform.MatchingEngineIndexEndpoint]:
        """Lazy load Vector Search Index Endpoint"""
        if self._index_endpoint is None:
            try:
                # 优先使用具体的 ID 如果有
                # if self.index_endpoint_id: ...
                
                endpoints = aiplatform.MatchingEngineIndexEndpoint.list(
                    filter=f'display_name="{self.vector_search_endpoint_name}"'
                )
                if endpoints:
                    self._index_endpoint = endpoints[0]
                    logger.info(f"Vector Search Endpoint connected: {self._index_endpoint.resource_name}")
                else:
                    logger.warning(f"Vector Search Endpoint not found: {self.vector_search_endpoint_name}")
            except Exception as e:
                logger.error(f"Failed to get Vector Search Endpoint: {e}")
        return self._index_endpoint

    async def get_user_embedding(self, user_id: str, risk_score: float) -> Optional[List[float]]:
        """
        调用 User Tower 获取用户向量
        """
        if not self.user_endpoint:
            logger.warning("User Endpoint unavailable")
            return None
            
        try:
            # 构造 Vertex AI Prediction 请求
            # 输入格式需符合 SavedModel signature
            instances = [{
                "user_id": user_id,
                "user_risk_score": risk_score
            }]
            
            # 异步执行同步调用
            loop = asyncio.get_event_loop()
            prediction = await loop.run_in_executor(
                None, 
                lambda: self.user_endpoint.predict(instances)
            )
            
            if prediction.predictions:
                # 假设输出 key 为 "output_1" 或 similar，通常是一个 list
                # TFRS 输出通常直接是 embedding list
                embedding = prediction.predictions[0]
                if isinstance(embedding, dict) and "output_1" in embedding:
                     return embedding["output_1"]
                return embedding # 列表形式
                
            return None
            
        except Exception as e:
            logger.error(f"User Embedding prediction failed: {e}")
            return None

    async def search_strategies(self, embedding: List[float], top_k: int = 3) -> List[Dict]:
        """
        在 Vector Search 中检索相似策略
        使用 Public Endpoint REST API 进行查询
        """
        if not self.index_endpoint:
            logger.warning("Index Endpoint unavailable")
            return []
            
        try:
            # 获取 Public Endpoint Domain
            public_domain = self.index_endpoint.public_endpoint_domain_name
            if not public_domain:
                logger.warning("No public endpoint domain found")
                return []
                
            # 查找已部署的 Index ID
            if not self.index_endpoint.deployed_indexes:
                logger.warning("No deployed indexes found on endpoint")
                return []
                
            deployed_index_id = self.index_endpoint.deployed_indexes[0].id
            
            # 使用 HTTP REST API 调用 Public Endpoint
            import google.auth
            import google.auth.transport.requests
            import requests
            
            # 获取认证凭据
            credentials, project = google.auth.default()
            auth_req = google.auth.transport.requests.Request()
            credentials.refresh(auth_req)
            
            # 构造请求
            url = f"https://{public_domain}/v1/projects/{self.project_id}/locations/{self.location}/indexEndpoints/{self.index_endpoint.name.split('/')[-1]}:findNeighbors"
            
            headers = {
                "Authorization": f"Bearer {credentials.token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "deployed_index_id": deployed_index_id,
                "queries": [{
                    "datapoint": {
                        "datapoint_id": "query",
                        "feature_vector": embedding
                    },
                    "neighbor_count": top_k
                }]
            }
            
            # 异步发送请求
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(url, json=payload, headers=headers, timeout=30)
            )
            
            if response.status_code != 200:
                logger.error(f"Vector search API error: {response.status_code} - {response.text}")
                return []
            
            # 解析结果
            data = response.json()
            neighbors = data.get("nearestNeighbors", [])
            if not neighbors:
                return []
                
            results = []
            for neighbor in neighbors[0].get("neighbors", []):
                datapoint = neighbor.get("datapoint", {})
                results.append({
                    "strategy_id": datapoint.get("datapointId", "unknown"),
                    "score": neighbor.get("distance", 0.0)
                })
                
            logger.info(f"Vector search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    async def get_recommendations(
        self, 
        user_id: str, 
        risk_score: float, 
        top_k: int = 3
    ) -> List[Dict]:
        """
        获取用户推荐策略 (完整流程)
        """
        with tracer.start_as_current_span("RecommendationService.get_recommendations") as span:
            span.set_attribute("user.id", user_id)
            span.set_attribute("risk.score", risk_score)
            
            # 1. 获取 User Embedding
            embedding = await self.get_user_embedding(user_id, risk_score)
            
            if not embedding:
                logger.warning("Failed to get user embedding, returning fallback")
                return self._get_fallback_strategies(risk_score)
                
            # 2. 向量检索
            search_results = await self.search_strategies(embedding, top_k)
            
            if not search_results:
                logger.warning("No search results, returning fallback")
                return self._get_fallback_strategies(risk_score)
            
            # 3. 补充详情 (Mock for now, should load from DB/CSV)
            recommendations = []
            for res in search_results:
                sid = res["strategy_id"]
                # 简单 Mock 内容，实际应读取 strategies.csv 或数据库
                recommendations.append({
                    "id": sid,
                    "score": res["score"],
                    "description": self._get_strategy_description(sid),
                    "type": self._infer_type(sid) 
                })
                
            return recommendations

    def _get_fallback_strategies(self, risk_score: float) -> List[Dict]:
        """降级策略"""
        if risk_score > 0.7:
            return [{
                "id": "FALLBACK_HIGH", 
                "description": "大力度挽留：首月 50% 折扣", 
                "type": "discount"
            }]
        else:
             return [{
                "id": "FALLBACK_LOW", 
                "description": "温馨关怀：新功能体验邀请", 
                "type": "email"
            }]

    def _get_strategy_description(self, sid: str) -> str:
        # TODO: Implement actual lookup
        return f"AI 推荐策略 ({sid})"

    def _infer_type(self, sid: str) -> str:
        # 这里只是演示，实际应查表
        return "mixed"

# 单例
_rec_service: Optional[RecommendationService] = None

def get_recommendation_service() -> RecommendationService:
    global _rec_service
    if _rec_service is None:
        _rec_service = RecommendationService()
    return _rec_service
