"""
SentinEL 消息队列服务
封装 Google Cloud Pub/Sub 消息发布逻辑
"""

import json
import logging
from typing import Optional
from google.cloud import pubsub_v1
from app.core.config import settings

logger = logging.getLogger(__name__)


class QueueService:
    """
    Pub/Sub 消息队列服务
    用于异步发布分析任务到消息队列
    """

    def __init__(self):
        self.publisher = pubsub_v1.PublisherClient()
        self.topic_path = self.publisher.topic_path(
            settings.PROJECT_ID,
            "sentinel-analysis-trigger"
        )

    def publish_analysis_event(
        self,
        user_id: str,
        analysis_id: str,
        image_data: Optional[str] = None
    ) -> str:
        """
        将分析请求发布到 Pub/Sub Topic

        Args:
            user_id: 目标用户 ID
            analysis_id: 预生成的分析记录 ID
            image_data: 可选的 Base64 编码图片数据

        Returns:
            str: Pub/Sub 消息 ID
        """
        # 构建消息负载
        message_data = {
            "user_id": user_id,
            "analysis_id": analysis_id,
        }

        # 图片数据单独传递（可能很大，作为属性或压缩）
        # 为简化，直接放入消息体（Pub/Sub 消息上限 10MB）
        if image_data:
            message_data["image_data"] = image_data

        # 序列化为 JSON 并编码为 bytes
        message_bytes = json.dumps(message_data).encode("utf-8")

        # 发布消息
        try:
            future = self.publisher.publish(
                self.topic_path,
                data=message_bytes,
                # 可选：添加属性用于过滤/路由
                user_id=user_id,
                analysis_id=analysis_id
            )
            message_id = future.result()
            logger.info(
                f"[QueueService] Published message {message_id} for analysis {analysis_id}"
            )
            return message_id
        except Exception as e:
            logger.error(f"[QueueService] Failed to publish message: {e}")
            raise


# 单例实例
# 单例实例
_queue_service_instance = None

def get_queue_service() -> Optional["QueueService"]:
    global _queue_service_instance
    if _queue_service_instance is None:
        try:
            _queue_service_instance = QueueService()
        except Exception as e:
            logger.error(f"Failed to initialize QueueService: {e}")
            return None
    return _queue_service_instance
