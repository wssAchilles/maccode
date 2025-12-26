"""
Feature Store Service (Online Serving)

功能:
    提供低延迟的实时特征读取服务，对接 Vertex AI Feature Store Online Serving。
    用于 orchestrated_service.py 在分析时获取用户的实时行为特征。

注意:
    需要 google-cloud-aiplatform SDK >= 1.38.0
"""

import logging
from typing import Dict, List, Optional, Any
from google.cloud import aiplatform

# Attempt to import Feature Service Client gracefully to prevent startup crashes
FeatureOnlineStoreServingServiceClient = None
FeatureViewDataKey = None
FetchFeatureValuesRequest = None

try:
    from google.cloud.aiplatform_v1 import FeatureOnlineStoreServingServiceClient
    from google.cloud.aiplatform_v1.types import (
        FeatureViewDataKey, 
        FetchFeatureValuesRequest
    )
except ImportError:
    # Try alternative path or log error
    try:
        from google.cloud.aiplatform_v1.services.feature_online_store_serving_service import FeatureOnlineStoreServingServiceClient
        from google.cloud.aiplatform_v1.types import FeatureViewDataKey, FetchFeatureValuesRequest
    except ImportError as e:
        logger = logging.getLogger(__name__)
        logger.error(f"CRITICAL: Could not import FeatureOnlineStoreServingServiceClient. Feature Store features will be disabled. Error: {e}")
        # We generally won't crash here, but service methods will fail if called.

from app.core.config import settings

logger = logging.getLogger(__name__)

class FeatureStoreService:
    def __init__(self, project_id: str = settings.PROJECT_ID, location: str = "us-central1"):
        self.project_id = project_id
        self.location = location
        self.feature_online_store = "sentinel_online_store"
        self.feature_view = "user_realtime_view"
        
        # 初始化客户端
        client_options = {"api_endpoint": f"{location}-aiplatform.googleapis.com"}
        self.client = FeatureOnlineStoreServingServiceClient(client_options=client_options)
        
        logger.info(f"FeatureStoreService initialized for store: {self.feature_online_store}")

    def get_online_features(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户的实时特征 (Low Latency)
        
        Args:
            user_id: 用户唯一标识
            
        Returns:
            Dict: 特征键值对，例如 {"rage_clicks_5m": 2, "active_session_duration": 120.5}
        """
        try:
            # 构造请求路径
            # projects/{project}/locations/{location}/featureOnlineStores/{store}/featureViews/{view}
            feature_view_resource = (
                f"projects/{self.project_id}/locations/{self.location}/"
                f"featureOnlineStores/{self.feature_online_store}/featureViews/{self.feature_view}"
            )
            
            # 构造数据键 (Entity ID)
            data_key = FeatureViewDataKey(key=user_id)
            
            # 发起请求
            request = FetchFeatureValuesRequest(
                feature_view=feature_view_resource,
                data_key=data_key,
                data_format=FetchFeatureValuesRequest.FeatureViewDataFormat.KEY_VALUE
            )
            
            # 同步调用 (FastAPI 可以用 run_in_executor 包装，或者使用异步 gRPC stub)
            # 这里为简单起见使用同步调用，因为 Vertex SDK 主要是同步的
            response = self.client.fetch_feature_values(request=request)
            
            # 解析结果
            features = {}
            if response.key_values:
                for feature in response.key_values.features:
                    # 根据类型转换值
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
            
            return features
            
        except Exception as e:
            logger.error(f"Failed to fetch online features for user {user_id}: {e}")
            # 降级策略: 返回空特征，避免阻塞主流程
            return {}

# 单例实例
_feature_store_service_instance = None

def get_feature_store_service() -> Optional["FeatureStoreService"]:
    """
    Lazy load singleton to avoid startup crashes if credentials missing
    """
    global _feature_store_service_instance
    if _feature_store_service_instance is None:
        try:
            _feature_store_service_instance = FeatureStoreService()
        except Exception as e:
            logger.error(f"Failed to initialize FeatureStoreService: {e}")
            return None
    return _feature_store_service_instance
