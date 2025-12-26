"""
SentinEL 预测服务
封装 Vertex AI Endpoint 调用，提供流失概率预测

功能:
    1. 从用户 ID 和事件序列获取流失概率
    2. 支持缓存以减少重复请求
    3. 异步调用以避免阻塞
    4. 降级策略：Endpoint 不可用时返回默认值

使用方法:
    from app.services.prediction_service import get_prediction_service
    
    service = get_prediction_service()
    prob = service.predict_churn(user_id="123", events=["page_view", "view_item", ...])

依赖:
    pip install google-cloud-aiplatform
"""

import logging
import json
import time
from typing import List, Optional, Dict, Any
from functools import lru_cache
import asyncio
from concurrent.futures import ThreadPoolExecutor

from google.cloud import aiplatform
from google.cloud.aiplatform import Endpoint

from app.core.config import settings
from app.core.telemetry import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer()


# ==============================================================================
# 事件词汇表 (与 extract_sequences.py 保持一致)
# ==============================================================================
EVENT_VOCAB: Dict[str, int] = {
    "<PAD>": 0,
    "<UNK>": 1,
    "page_view": 2,
    "view_item": 3,
    "add_to_cart": 4,
    "remove_from_cart": 5,
    "begin_checkout": 6,
    "add_payment_info": 7,
    "purchase": 8,
    "view_promotion": 9,
    "select_promotion": 10,
    "check_policy": 11,
    "view_returns": 12,
    "contact_support": 13,
    "rage_click": 14,
    "session_start": 15,
    "session_end": 16,
    "scroll_to_bottom": 17,
    "form_abandon": 18,
    "coupon_apply": 19,
    "coupon_fail": 20,
    "wishlist_add": 21,
    "wishlist_remove": 22,
    "search": 23,
    "filter_apply": 24,
    "compare_items": 25,
    "share_item": 26,
    "review_read": 27,
    "review_write": 28,
}


# ==============================================================================
# 配置
# ==============================================================================
DEFAULT_SEQ_LENGTH = 20
DEFAULT_ENDPOINT_NAME = "sentinel-churn-endpoint"
CACHE_TTL_SECONDS = 300  # 缓存 5 分钟


class PredictionService:
    """
    流失预测服务
    
    封装 Vertex AI Endpoint 调用，提供统一的预测接口。
    
    Attributes:
        project_id: GCP 项目 ID
        region: Vertex AI 区域
        endpoint_name: Endpoint 显示名称
        seq_length: 序列长度
    """
    
    def __init__(
        self,
        project_id: str = settings.PROJECT_ID,
        region: str = settings.LOCATION,
        endpoint_name: str = DEFAULT_ENDPOINT_NAME,
        seq_length: int = DEFAULT_SEQ_LENGTH
    ):
        """
        初始化预测服务
        
        Args:
            project_id: GCP 项目 ID
            region: 区域（如 us-central1）
            endpoint_name: Vertex AI Endpoint 显示名称
            seq_length: 输入序列长度
        """
        self.project_id = project_id
        self.region = region
        self.endpoint_name = endpoint_name
        self.seq_length = seq_length
        self._endpoint: Optional[Endpoint] = None
        self._cache: Dict[str, tuple] = {}  # {cache_key: (timestamp, probability)}
        self._executor = ThreadPoolExecutor(max_workers=4)
        
        # 初始化 Vertex AI
        aiplatform.init(project=project_id, location=region)
        
        logger.info(f"PredictionService 初始化 | Endpoint: {endpoint_name}")
    
    @property
    def endpoint(self) -> Optional[Endpoint]:
        """
        懒加载 Endpoint 引用
        """
        if self._endpoint is None:
            try:
                endpoints = Endpoint.list(
                    filter=f'display_name="{self.endpoint_name}"'
                )
                if endpoints:
                    self._endpoint = endpoints[0]
                    logger.info(f"Endpoint 已连接: {self._endpoint.resource_name}")
                else:
                    logger.warning(f"Endpoint 未找到: {self.endpoint_name}")
            except Exception as e:
                logger.error(f"获取 Endpoint 失败: {e}")
        return self._endpoint
    
    def tokenize_events(self, events: List[str]) -> List[int]:
        """
        将事件名称转换为 Token ID 序列
        
        Args:
            events: 事件名称列表（如 ["page_view", "view_item", ...]）
            
        Returns:
            List[int]: Token ID 序列，长度为 seq_length
        """
        # 转换为 Token IDs
        token_ids = [
            EVENT_VOCAB.get(e.lower().strip(), EVENT_VOCAB["<UNK>"])
            for e in events
        ]
        
        # Pad/Truncate
        if len(token_ids) >= self.seq_length:
            return token_ids[-self.seq_length:]
        else:
            padding = [EVENT_VOCAB["<PAD>"]] * (self.seq_length - len(token_ids))
            return padding + token_ids
    
    def _get_cache_key(self, user_id: str, events: List[str]) -> str:
        """生成缓存键"""
        events_hash = hash(tuple(events[-10:]))  # 只用最近 10 个事件
        return f"{user_id}:{events_hash}"
    
    def _check_cache(self, cache_key: str) -> Optional[float]:
        """检查缓存"""
        if cache_key in self._cache:
            timestamp, probability = self._cache[cache_key]
            if time.time() - timestamp < CACHE_TTL_SECONDS:
                logger.debug(f"缓存命中: {cache_key}")
                return probability
            else:
                del self._cache[cache_key]
        return None
    
    def _update_cache(self, cache_key: str, probability: float):
        """更新缓存"""
        self._cache[cache_key] = (time.time(), probability)
        
        # 简单的缓存清理（保留最近 1000 条）
        if len(self._cache) > 1000:
            # 删除最旧的一半
            sorted_keys = sorted(self._cache.keys(), key=lambda k: self._cache[k][0])
            for key in sorted_keys[:500]:
                del self._cache[key]
    
    def predict_churn(
        self,
        user_id: str,
        events: List[str],
        use_cache: bool = True
    ) -> float:
        """
        预测用户流失概率
        
        Args:
            user_id: 用户 ID
            events: 用户最近的事件序列（事件名称列表）
            use_cache: 是否使用缓存
            
        Returns:
            float: 流失概率 (0.0 - 1.0)
            
        Raises:
            无异常抛出，失败时返回 0.5（中性值）
        """
        with tracer.start_as_current_span("PredictionService.predict_churn") as span:
            span.set_attribute("user.id", user_id)
            span.set_attribute("events.count", len(events))
            
            # 检查缓存
            if use_cache:
                cache_key = self._get_cache_key(user_id, events)
                cached = self._check_cache(cache_key)
                if cached is not None:
                    span.set_attribute("cache.hit", True)
                    return cached
            
            span.set_attribute("cache.hit", False)
            
            # 检查 Endpoint 可用性
            if self.endpoint is None:
                logger.warning("Endpoint 不可用，返回默认概率")
                span.set_attribute("fallback", True)
                return 0.5
            
            try:
                # Tokenize
                token_ids = self.tokenize_events(events)
                
                # 构造请求
                instances = [{"sequence": token_ids}]
                
                # 调用 Endpoint
                prediction = self.endpoint.predict(instances)
                
                # 解析结果
                # 假设模型返回格式: [[probability]]
                if prediction.predictions:
                    probability = float(prediction.predictions[0])
                    if isinstance(probability, list):
                        probability = probability[0]
                else:
                    probability = 0.5
                
                # 裁剪到 [0, 1] 范围
                probability = max(0.0, min(1.0, probability))
                
                # 更新缓存
                if use_cache:
                    self._update_cache(cache_key, probability)
                
                span.set_attribute("prediction.probability", probability)
                logger.info(f"预测完成 | user={user_id}, probability={probability:.4f}")
                
                return probability
                
            except Exception as e:
                logger.error(f"预测失败: {e}")
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                # 降级：返回中性值
                return 0.5
    
    async def predict_churn_async(
        self,
        user_id: str,
        events: List[str],
        use_cache: bool = True
    ) -> float:
        """
        异步预测用户流失概率
        
        使用线程池执行同步 API 调用，避免阻塞事件循环。
        
        Args:
            user_id: 用户 ID
            events: 事件序列
            use_cache: 是否使用缓存
            
        Returns:
            float: 流失概率
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            lambda: self.predict_churn(user_id, events, use_cache)
        )
    
    def get_risk_level(self, probability: float) -> str:
        """
        根据概率返回风险等级
        
        Args:
            probability: 流失概率
            
        Returns:
            str: "High", "Medium", 或 "Low"
        """
        if probability >= 0.7:
            return "High"
        elif probability >= 0.4:
            return "Medium"
        else:
            return "Low"
    
    def analyze_sequence_risk_factors(self, events: List[str]) -> Dict[str, Any]:
        """
        分析序列中的风险因素
        
        识别高风险事件模式。
        
        Args:
            events: 事件序列
            
        Returns:
            Dict: 风险因素分析结果
        """
        high_risk_events = {"check_policy", "view_returns", "rage_click", 
                           "contact_support", "remove_from_cart", "form_abandon"}
        positive_events = {"purchase", "add_to_cart", "coupon_apply"}
        
        risk_count = sum(1 for e in events if e.lower() in high_risk_events)
        positive_count = sum(1 for e in events if e.lower() in positive_events)
        
        # 检测愤怒点击模式
        rage_clicks = events.count("rage_click")
        
        return {
            "high_risk_event_count": risk_count,
            "positive_event_count": positive_count,
            "rage_click_count": rage_clicks,
            "last_event": events[-1] if events else None,
            "risk_ratio": risk_count / max(len(events), 1)
        }


# ==============================================================================
# 单例模式
# ==============================================================================
_prediction_service_instance: Optional[PredictionService] = None


def get_prediction_service() -> Optional[PredictionService]:
    """
    获取 PredictionService 单例
    
    如果初始化失败，返回 None。
    
    Returns:
        Optional[PredictionService]: 服务实例或 None
    """
    global _prediction_service_instance
    
    if _prediction_service_instance is None:
        try:
            _prediction_service_instance = PredictionService()
        except Exception as e:
            logger.error(f"PredictionService 初始化失败: {e}")
            return None
    
    return _prediction_service_instance
