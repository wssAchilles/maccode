"""
SentinEL 实时流量模拟器 (Live Traffic Generator)

功能:
    模拟高并发的用户点击流数据，并发送到 Google Cloud Pub/Sub Topic。
    用于测试实时数据管道 (Dataflow) 和 Feature Store 的性能。

使用方法:
    python simulation/live_traffic_gen.py --project_id YOUR_PROJECT_ID --topic_id sentinel-clickstream-topic --users 1000 --rate 50

依赖:
    pip install google-cloud-pubsub faker
"""

import argparse
import time
import json
import random
import logging
import threading
import uuid
from datetime import datetime
from typing import List, Dict, Any
from concurrent import futures

from google.cloud import pubsub_v1
from faker import Faker

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# 事件类型定义
EVENT_TYPES = [
    "view_item",        # 查看商品
    "add_to_cart",      # 加入购物车
    "check_policy",     # 查看退货政策 (风险信号)
    "rage_click",       # 愤怒点击 (高风险信号)
    "checkout_start",   # 开始结账
    "contact_support"   # 联系客服
]

# 事件权重 (模拟真实分布)
EVENT_WEIGHTS = [0.4, 0.2, 0.15, 0.05, 0.15, 0.05]

class TrafficGenerator:
    def __init__(self, project_id: str, topic_id: str, num_users: int, events_per_sec: float):
        """
        初始化流量生成器
        
        Args:
            project_id: GCP 项目 ID
            topic_id: Pub/Sub Topic 名称
            num_users: 模拟活跃用户数
            events_per_sec: 目标发送速率 (事件/秒)
        """
        self.project_id = project_id
        self.topic_id = topic_id
        self.num_users = num_users
        self.events_per_sec = events_per_sec
        self.publisher = pubsub_v1.PublisherClient()
        self.topic_path = self.publisher.topic_path(project_id, topic_id)
        self.fake = Faker()
        self.user_pool = [self._generate_user() for _ in range(num_users)]
        self.running = False
        self.total_sent = 0
        self.lock = threading.Lock()

    def _generate_user(self) -> Dict[str, Any]:
        """生成模拟用户基础信息"""
        return {
            "user_id": str(random.randint(10000, 99999)), # 使用简单的 ID 以便调试
            "device_id": str(uuid.uuid4()),
            "platform": random.choice(["ios", "android", "web"]),
            "country": self.fake.country_code()
        }

    def _create_event(self) -> Dict[str, Any]:
        """创建一个随机用户行为事件"""
        user = random.choice(self.user_pool)
        event_type = random.choices(EVENT_TYPES, weights=EVENT_WEIGHTS, k=1)[0]
        
        # 构造事件 Payload
        event = {
            "event_id": str(uuid.uuid4()),
            "user_id": user["user_id"],
            "session_id": str(uuid.uuid4()), # 简化：每次随机 session
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z", # ISO 8601 UTC
            "url": self.fake.uri_path(),
            "metadata": {
                "device_id": user["device_id"],
                "platform": user["platform"],
                "geo": user["country"]
            }
        }
        
        # 针对特定事件添加上下文
        if event_type == "view_item":
            event["metadata"]["item_id"] = str(random.randint(100, 500))
            event["metadata"]["price"] = round(random.uniform(10.0, 500.0), 2)
        elif event_type == "rage_click":
            event["metadata"]["click_count"] = random.randint(5, 20)
            
        return event

    def _publish_callback(self, future: futures.Future, data: str):
        """发布回调，处理结果"""
        try:
            future.result() # 如果有异常会在这里抛出
            with self.lock:
                self.total_sent += 1
                if self.total_sent % 100 == 0:
                    logger.info(f"已发送 {self.total_sent} 个事件")
        except Exception as e:
            logger.error(f"发布失败: {e} | Data: {data}")

    def start(self):
        """启动生成器 (阻塞模式)"""
        self.running = True
        logger.info(f"开始模拟流量... 目标速率: {self.events_per_sec} eps | 用户池: {self.num_users}")
        
        delay = 1.0 / self.events_per_sec
        
        try:
            while self.running:
                start_time = time.time()
                
                # 生成并发送事件
                event = self._create_event()
                data_str = json.dumps(event)
                data_bytes = data_str.encode("utf-8")
                
                # 异步发送
                publish_future = self.publisher.publish(self.topic_path, data_bytes)
                publish_future.add_done_callback(lambda f, d=data_str: self._publish_callback(f, d))
                
                # 控制发送速率
                elapsed = time.time() - start_time
                sleep_time = max(0, delay - elapsed)
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """停止生成器"""
        self.running = False
        logger.info(f"流量模拟停止. 总共发送: {self.total_sent} 个事件")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SentinEL Live Traffic Generator")
    parser.add_argument("--project_id", required=True, help="GCP Project ID")
    parser.add_argument("--topic_id", default="sentinel-clickstream-topic", help="Pub/Sub Topic ID")
    parser.add_argument("--users", type=int, default=100, help="Number of simulated users")
    parser.add_argument("--rate", type=float, default=10.0, help="Events per second")
    
    args = parser.parse_args()
    
    generator = TrafficGenerator(
        project_id=args.project_id,
        topic_id=args.topic_id,
        num_users=args.users,
        events_per_sec=args.rate
    )
    
    generator.start()
