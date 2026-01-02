"""
SentinEL 预测服务
封装 Vertex AI Endpoint 调用 + Feature Store 实时特征，提供混合推理

功能:
    1. 从 LSTM/Transformer 模型获取基础流失概率
    2. 从 Feature Store 读取实时用户特征 (rage_clicks_5m, active_session_duration 等)
    3. 混合推理: 使用实时特征动态调整预测结果
    4. 支持缓存、异步调用、降级策略

使用方法:
    from app.services.prediction_service import get_prediction_service
    
    service = get_prediction_service()
    prob = service.predict_churn(user_id="123", events=["page_view", "view_item", ...])

依赖:
    pip install google-cloud-aiplatform>=1.38.0
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


# =============================================================================
# Feature Store 客户端导入 (兼容处理)
# =============================================================================
FeatureOnlineStoreServingServiceClient = None
FeatureViewDataKey = None
FetchFeatureValuesRequest = None

try:
    from google.cloud.aiplatform_v1 import FeatureOnlineStoreServingServiceClient
    from google.cloud.aiplatform_v1.types import (
        FeatureViewDataKey, 
        FetchFeatureValuesRequest
    )
    FEATURE_STORE_AVAILABLE = True
except ImportError:
    try:
        from google.cloud.aiplatform_v1.services.feature_online_store_serving_service import FeatureOnlineStoreServingServiceClient
        from google.cloud.aiplatform_v1.types import FeatureViewDataKey, FetchFeatureValuesRequest
        FEATURE_STORE_AVAILABLE = True
    except ImportError as e:
        logger.warning(f"Feature Store SDK 不可用，实时特征将被禁用: {e}")
        FEATURE_STORE_AVAILABLE = False


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
DEFAULT_ENDPOINT_NAME = "sentinel-churn-endpoint"          # 旧 LSTM Endpoint (Blue)
DEFAULT_ENDPOINT_SHADOW = "sentinel-churn-transformer"     # 新 Transformer Endpoint (Green)
DEFAULT_SHADOW_WEIGHT = 0.0  # 0-1 之间，控制灰度/金丝雀流量
CACHE_TTL_SECONDS = 300  # 缓存 5 分钟

# Feature Store 配置
DEFAULT_FEATURE_ONLINE_STORE = "sentinel_online_store"
DEFAULT_FEATURE_VIEW = "user_realtime_view"
FEATURE_STORE_TIMEOUT_MS = 100  # Feature Store 超时阈值 (毫秒)

# Transformer 模型输入配置
TRANSFORMER_EVENT_SEQ_LEN = 20       # 事件序列长度
TRANSFORMER_STATIC_CAT_LEN = 3       # 分类特征长度
TRANSFORMER_STATIC_NUM_LEN = 5       # 数值特征长度


class PredictionService:
    """
    流失预测服务 (混合推理)
    
    封装 Vertex AI Endpoint 调用 + Feature Store 实时特征读取，
    提供基于深度学习模型和实时信号的联合预测。
    
    Attributes:
        project_id: GCP 项目 ID
        region: Vertex AI 区域
        endpoint_name: Endpoint 显示名称
        seq_length: 序列长度
        feature_online_store: Feature Online Store 名称
        feature_view: Feature View 名称
    """
    
    def __init__(
        self,
        project_id: str = settings.PROJECT_ID,
        region: str = settings.LOCATION,
        endpoint_name: str = DEFAULT_ENDPOINT_NAME,
        seq_length: int = DEFAULT_SEQ_LENGTH,
        shadow_endpoint_name: Optional[str] = None,
        shadow_weight: float = DEFAULT_SHADOW_WEIGHT,
        feature_online_store: str = DEFAULT_FEATURE_ONLINE_STORE,
        feature_view: str = DEFAULT_FEATURE_VIEW,
    ):
        """
        初始化预测服务
        
        Args:
            project_id: GCP 项目 ID
            region: 区域（如 us-central1）
            endpoint_name: Vertex AI Endpoint 显示名称
            seq_length: 输入序列长度
            shadow_endpoint_name: 金丝雀 Endpoint 名称
            shadow_weight: 金丝雀流量权重
            feature_online_store: Feature Online Store 名称
            feature_view: Feature View 名称
        """
        self.project_id = project_id
        self.region = region
        self.endpoint_name = endpoint_name
        self.seq_length = seq_length
        self.shadow_endpoint_name = shadow_endpoint_name or DEFAULT_ENDPOINT_SHADOW
        self.shadow_weight = max(0.0, min(1.0, shadow_weight))
        self.feature_online_store = feature_online_store
        self.feature_view = feature_view

        self._endpoint: Optional[Endpoint] = None
        self._shadow_endpoint: Optional[Endpoint] = None
        self._feature_store_client = None
        self._cache: Dict[str, tuple] = {}  # {cache_key: (timestamp, probability)}
        self._executor = ThreadPoolExecutor(max_workers=4)
        
        # 初始化 Vertex AI
        aiplatform.init(project=project_id, location=region)
        
        # 初始化 Feature Store 客户端
        self._init_feature_store_client()
        
        logger.info(
            f"PredictionService 初始化 | Endpoint: {endpoint_name} | "
            f"FeatureStore: {feature_online_store}/{feature_view}"
        )
    
    def _init_feature_store_client(self):
        """初始化 Feature Store 客户端"""
        if FEATURE_STORE_AVAILABLE and FeatureOnlineStoreServingServiceClient:
            try:
                client_options = {"api_endpoint": f"{self.region}-aiplatform.googleapis.com"}
                self._feature_store_client = FeatureOnlineStoreServingServiceClient(
                    client_options=client_options
                )
                logger.info(f"Feature Store 客户端初始化成功: {self.feature_online_store}")
            except Exception as e:
                logger.error(f"Feature Store 客户端初始化失败: {e}")
                self._feature_store_client = None
        else:
            logger.warning("Feature Store SDK 不可用，实时特征将被禁用")
            self._feature_store_client = None
    
    def _build_feature_view_path(self) -> str:
        """构造 Feature View 资源路径"""
        return (
            f"projects/{self.project_id}/locations/{self.region}/"
            f"featureOnlineStores/{self.feature_online_store}/"
            f"featureViews/{self.feature_view}"
        )
    
    def _get_realtime_features_sync(self, user_id: str) -> Dict[str, Any]:
        """
        同步读取用户实时特征 (内部方法)
        
        Args:
            user_id: 用户 ID
            
        Returns:
            Dict: 特征键值对，如 {"rage_clicks_5m": 2, "active_session_duration": 120.5}
                  失败时返回空字典
        """
        if self._feature_store_client is None:
            return {}
        
        start_time = time.time()
        
        try:
            feature_view_path = self._build_feature_view_path()
            data_key = FeatureViewDataKey(key=user_id)
            
            request = FetchFeatureValuesRequest(
                feature_view=feature_view_path,
                data_key=data_key,
                data_format=FetchFeatureValuesRequest.FeatureViewDataFormat.KEY_VALUE
            )
            
            response = self._feature_store_client.fetch_feature_values(request=request)
            
            # 解析特征值
            features = {}
            if response.key_values:
                for feature in response.key_values.features:
                    val = None
                    if feature.value.HasField("int64_value"):
                        val = feature.value.int64_value
                    elif feature.value.HasField("double_value"):
                        val = feature.value.double_value
                    elif feature.value.HasField("string_value"):
                        val = feature.value.string_value
                    elif feature.value.HasField("bool_value"):
                        val = feature.value.bool_value
                    features[feature.name] = val
            
            latency_ms = (time.time() - start_time) * 1000
            logger.info(
                f"Feature Store 读取成功 | user={user_id} | latency={latency_ms:.1f}ms | "
                f"features={features}"
            )
            
            return features
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.warning(
                f"Feature Store 读取失败 | user={user_id} | latency={latency_ms:.1f}ms | "
                f"error={e} | 降级为空特征"
            )
            return {}
    
    async def _get_realtime_features(self, user_id: str) -> Dict[str, Any]:
        """
        异步读取用户实时特征 (非阻塞)
        
        使用线程池避免阻塞事件循环，并设置超时保护。
        
        Args:
            user_id: 用户 ID
            
        Returns:
            Dict: 特征键值对，失败或超时返回空字典
        """
        loop = asyncio.get_event_loop()
        
        try:
            # 使用 wait_for 设置超时
            features = await asyncio.wait_for(
                loop.run_in_executor(
                    self._executor,
                    lambda: self._get_realtime_features_sync(user_id)
                ),
                timeout=FEATURE_STORE_TIMEOUT_MS / 1000.0  # 转换为秒
            )
            return features
            
        except asyncio.TimeoutError:
            logger.warning(
                f"Feature Store 读取超时 | user={user_id} | "
                f"timeout={FEATURE_STORE_TIMEOUT_MS}ms | 降级为空特征"
            )
            return {}
        except Exception as e:
            logger.warning(f"Feature Store 异步读取异常: {e}")
            return {}
    
    def _apply_realtime_adjustment(
        self, 
        base_probability: float, 
        realtime_features: Dict[str, Any]
    ) -> float:
        """
        应用实时特征调整基础概率 (混合推理核心逻辑)
        
        策略:
        - 愤怒点击 > 0: 大幅增加流失风险 (+0.20)
        - 活跃会话时长 > 300秒: 轻微降低风险 (-0.05)
        - 查看政策次数 > 2: 中度增加风险 (+0.10)
        - 购物车添加 > 0: 轻微降低风险 (-0.03)
        
        Args:
            base_probability: LSTM/Transformer 模型基础概率
            realtime_features: Feature Store 实时特征
            
        Returns:
            float: 调整后的最终概率 [0.0, 1.0]
        """
        final_probability = base_probability
        
        # 1. 愤怒点击检测 (高风险信号)
        rage_clicks = realtime_features.get("rage_clicks_5m", 0) or 0
        if rage_clicks > 0:
            adjustment = min(0.2, rage_clicks * 0.1)  # 每次愤怒点击 +10%, 最多 +20%
            final_probability = min(1.0, final_probability + adjustment)
            logger.debug(f"愤怒点击调整: +{adjustment:.2f} (count={rage_clicks})")
        
        # 2. 活跃会话时长 (正向信号)
        session_duration = realtime_features.get("active_session_duration", 0) or 0
        if session_duration > 300:  # 超过 5 分钟
            adjustment = min(0.05, (session_duration - 300) / 1000)  # 最多 -5%
            final_probability = max(0.0, final_probability - adjustment)
            logger.debug(f"活跃会话调整: -{adjustment:.2f} (duration={session_duration}s)")
        
        # 3. 查看政策次数 (风险信号)
        policy_views = realtime_features.get("policy_views_5m", 0) or 0
        if policy_views > 2:
            adjustment = min(0.1, (policy_views - 2) * 0.05)  # 每超出一次 +5%, 最多 +10%
            final_probability = min(1.0, final_probability + adjustment)
            logger.debug(f"政策查看调整: +{adjustment:.2f} (count={policy_views})")
        
        # 4. 购物车添加 (正向信号)
        cart_adds = realtime_features.get("cart_additions_5m", 0) or 0
        if cart_adds > 0:
            adjustment = min(0.03, cart_adds * 0.01)  # 每次 +1%, 最多 -3%
            final_probability = max(0.0, final_probability - adjustment)
            logger.debug(f"购物车添加调整: -{adjustment:.2f} (count={cart_adds})")
        
        return final_probability
    
    def _get_endpoint(self, display_name: str) -> Optional[Endpoint]:
        """Lazy load by display_name."""
        try:
            endpoints = Endpoint.list(filter=f'display_name="{display_name}"')
            if endpoints:
                logger.info(f"Endpoint 已连接: {endpoints[0].resource_name}")
                return endpoints[0]
            logger.warning(f"Endpoint 未找到: {display_name}")
        except Exception as e:
            logger.error(f"获取 Endpoint 失败 ({display_name}): {e}")
        return None
    
    def _get_endpoint_by_id(self, endpoint_id: str) -> Optional[Endpoint]:
        """
        通过 Endpoint ID 获取 Endpoint 对象
        
        Args:
            endpoint_id: Vertex AI Endpoint ID
            
        Returns:
            Optional[Endpoint]: Endpoint 对象或 None
        """
        try:
            resource_name = f"projects/{self.project_id}/locations/{self.region}/endpoints/{endpoint_id}"
            endpoint = Endpoint(endpoint_name=resource_name)
            logger.info(f"Endpoint (by ID) 已连接: {resource_name}")
            return endpoint
        except Exception as e:
            logger.error(f"通过 ID 获取 Endpoint 失败 ({endpoint_id}): {e}")
            return None

    @property
    def endpoint(self) -> Optional[Endpoint]:
        """Primary endpoint (Blue)."""
        if self._endpoint is None:
            self._endpoint = self._get_endpoint(self.endpoint_name)
        return self._endpoint

    @property
    def shadow_endpoint(self) -> Optional[Endpoint]:
        """Shadow/Green endpoint for金丝雀/灰度."""
        if self.shadow_weight <= 0:
            return None
        if self._shadow_endpoint is None and self.shadow_endpoint_name:
            self._shadow_endpoint = self._get_endpoint(self.shadow_endpoint_name)
        return self._shadow_endpoint

    def _choose_endpoint(self) -> Optional[Endpoint]:
        """
        简单金丝雀路由：按权重选择 shadow，否则 primary。
        """
        import random
        if self.shadow_endpoint and random.random() < self.shadow_weight:
            return self.shadow_endpoint
        return self.endpoint
    
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
    
    def _assemble_transformer_input(
        self,
        user_id: str,
        events: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        组装模型输入数据
        
        注意: 当前 serve.py 服务器期望 'sequence' 字段，
        并在内部自动构建 static_categorical 和 static_numerical 的 Dummy 数据。
        
        Args:
            user_id: 用户 ID
            events: 事件序列 (可选)
            
        Returns:
            Dict: 符合服务器要求的输入格式 {"sequence": List[int]}
        """
        import random
        import hashlib
        
        # 如果有事件则 tokenize，否则生成基于 user_id 的伪随机序列
        if events:
            event_seq = self.tokenize_events(events)
        else:
            # 基于 user_id 生成确定性的伪随机序列 (便于复现)
            seed = int(hashlib.md5(user_id.encode()).hexdigest()[:8], 16)
            random.seed(seed)
            event_seq = [random.randint(1, len(EVENT_VOCAB) - 1) for _ in range(TRANSFORMER_EVENT_SEQ_LEN)]
        
        # 服务器 (serve.py) 期望 'sequence' 字段
        # 它会在内部自动填充 static_categorical 和 static_numerical
        return {"sequence": event_seq}
    
    def predict_churn(
        self,
        user_id: str,
        events: List[str],
        use_cache: bool = True
    ) -> float:
        """
        预测用户流失概率 (混合推理)
        
        流程:
        1. 调用 LSTM/Transformer 模型获取基础概率
        2. 从 Feature Store 读取实时特征
        3. 应用实时特征调整公式
        4. 返回最终概率
        
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
            
            # 检查缓存 (注意: 混合推理时缓存可能导致实时性下降，按需禁用)
            cache_key = None
            if use_cache:
                cache_key = self._get_cache_key(user_id, events)
                cached = self._check_cache(cache_key)
                if cached is not None:
                    span.set_attribute("cache.hit", True)
                    return cached
            
            span.set_attribute("cache.hit", False)
            
            # ================ Step 1: 获取基础概率 ================
            base_probability = 0.5  # 默认中性值
            
            ep = self._choose_endpoint()
            if ep is None:
                logger.warning("Endpoint 不可用，使用默认基础概率 0.5")
                span.set_attribute("fallback.endpoint", True)
            else:
                try:
                    # 使用新的 Transformer 输入格式
                    # 优先使用 Endpoint ID 直接获取 Endpoint
                    transformer_endpoint = None
                    if hasattr(settings, 'VERTEX_ENDPOINT_ID') and settings.VERTEX_ENDPOINT_ID:
                        transformer_endpoint = self._get_endpoint_by_id(settings.VERTEX_ENDPOINT_ID)
                    
                    if transformer_endpoint is None:
                        transformer_endpoint = ep
                    
                    if transformer_endpoint is None:
                        logger.warning("无可用 Endpoint，使用默认基础概率 0.5")
                        span.set_attribute("fallback.no_endpoint", True)
                    else:
                        # 组装 Transformer 输入
                        transformer_input = self._assemble_transformer_input(user_id, events)
                        instances = [transformer_input]
                        
                        logger.info(f"Transformer 输入 | sequence_len={len(transformer_input['sequence'])}")
                        
                        # 调用 Endpoint
                        prediction = transformer_endpoint.predict(instances)
                        
                        # 解析结果: predictions 格式为 [0.255] 或 [[0.255]]
                        if prediction.predictions:
                            result = prediction.predictions[0]
                            if isinstance(result, list):
                                base_probability = float(result[0])
                            else:
                                base_probability = float(result)
                        
                        # 裁剪到 [0, 1] 范围
                        base_probability = max(0.0, min(1.0, base_probability))
                        
                except Exception as e:
                    logger.error(f"Endpoint 预测失败: {e}")
                    span.set_attribute("error.endpoint", True)
                    span.set_attribute("error.message", str(e))
            
            span.set_attribute("prediction.base_probability", base_probability)
            
            # ================ Step 2: 获取实时特征 ================
            realtime_features = {}
            feature_store_latency_ms = 0
            
            try:
                start_time = time.time()
                realtime_features = self._get_realtime_features_sync(user_id)
                feature_store_latency_ms = (time.time() - start_time) * 1000
            except Exception as e:
                logger.warning(f"Feature Store 读取异常: {e}")
            
            span.set_attribute("feature_store.latency_ms", feature_store_latency_ms)
            span.set_attribute("realtime.rage_clicks", realtime_features.get("rage_clicks_5m", 0))
            span.set_attribute("realtime.session_duration", realtime_features.get("active_session_duration", 0))
            span.set_attribute("realtime.policy_views", realtime_features.get("policy_views_5m", 0))
            
            # ================ Step 3: 混合推理调整 ================
            final_probability = self._apply_realtime_adjustment(
                base_probability, 
                realtime_features
            )
            
            span.set_attribute("prediction.final_probability", final_probability)
            span.set_attribute("prediction.adjustment", final_probability - base_probability)
            
            # 更新缓存
            if use_cache and cache_key:
                self._update_cache(cache_key, final_probability)
            
            logger.info(
                f"混合推理完成 | user={user_id} | base={base_probability:.4f} | "
                f"final={final_probability:.4f} | adjustment={final_probability - base_probability:+.4f} | "
                f"realtime_features={realtime_features}"
            )
            
            return final_probability
    
    async def predict_churn_async(
        self,
        user_id: str,
        events: List[str],
        use_cache: bool = True
    ) -> float:
        """
        异步预测用户流失概率 (混合推理)
        
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
            _prediction_service_instance = PredictionService(
                endpoint_name=settings.CHURN_ENDPOINT_PRIMARY,
                shadow_endpoint_name=settings.CHURN_ENDPOINT_SHADOW,
                shadow_weight=settings.CHURN_ENDPOINT_SHADOW_WEIGHT,
                seq_length=settings.CHURN_SEQ_LENGTH,
            )
        except Exception as e:
            logger.error(f"PredictionService 初始化失败: {e}")
            return None
    
    return _prediction_service_instance
