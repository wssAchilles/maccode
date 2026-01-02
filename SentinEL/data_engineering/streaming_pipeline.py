"""
SentinEL 实时流式计算管道 (Streaming Pipeline)

功能:
    1. 从 Google Cloud Pub/Sub 读取点击流事件 (JSON)
    2. 应用滑动窗口 (Sliding Windows) 进行聚合计算
    3. 解析用户行为特征 (如 rage_click 次数, policy_views)
    4. 将聚合后的特征直接写入 Vertex AI Feature Store Online Store (低延迟)

运行方式:
    python data_engineering/streaming_pipeline.py \
        --project YOUR_PROJECT_ID \
        --region us-central1 \
        --input_subscription projects/YOUR_PROJECT_ID/subscriptions/sentinel-clickstream-sub \
        --feature_online_store sentinel_online_store \
        --feature_view user_realtime_view \
        --runner DataflowRunner \
        --job_name sentinel-streaming-features

依赖:
    pip install apache-beam[gcp] google-cloud-aiplatform>=1.38.0
"""

import argparse
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions, GoogleCloudOptions
from apache_beam import window
from apache_beam import pvalue

# =============================================================================
# Feature Store 客户端导入 (兼容处理)
# =============================================================================
WriteFeatureValuesRequest = None
WriteFeatureValuesPayload = None
FeatureValue = None
FeatureOnlineStoreAdminServiceClient = None

try:
    from google.cloud.aiplatform_v1 import FeatureOnlineStoreAdminServiceClient
    from google.cloud.aiplatform_v1.types import (
        WriteFeatureValuesRequest,
        WriteFeatureValuesPayload,
        FeatureValue,
    )
    FEATURE_STORE_AVAILABLE = True
except ImportError:
    try:
        # 备用导入路径
        from google.cloud.aiplatform_v1.services.feature_online_store_admin_service import FeatureOnlineStoreAdminServiceClient
        from google.cloud.aiplatform_v1.types import WriteFeatureValuesRequest, WriteFeatureValuesPayload, FeatureValue
        FEATURE_STORE_AVAILABLE = True
    except ImportError as e:
        logging.warning(f"Feature Store SDK 不可用，将使用降级模式: {e}")
        FEATURE_STORE_AVAILABLE = False


# =============================================================================
# 配置常量
# =============================================================================
DEFAULT_FEATURE_ONLINE_STORE = "sentinel_online_store"
DEFAULT_FEATURE_VIEW = "user_realtime_view"
BATCH_SIZE = 100  # 微批次大小
MAX_RETRIES = 3   # 最大重试次数
RETRY_BASE_DELAY = 0.5  # 指数退避基础延迟 (秒)


# =============================================================================
# DoFn: 事件解析
# =============================================================================
class ParseEventFn(beam.DoFn):
    """解析 JSON 事件并添加处理时间戳"""
    def process(self, element):
        try:
            event = json.loads(element.decode("utf-8"))
            yield event
        except Exception as e:
            logging.error(f"解析事件失败: {e}")


# =============================================================================
# DoFn: 特征提取
# =============================================================================
class ExtractUserFeaturesFn(beam.DoFn):
    """提取关键特征并以 (user_id, feature_dict) 形式输出"""
    def process(self, event):
        user_id = event.get("user_id")
        event_type = event.get("event_type")
        timestamp = event.get("timestamp")
        
        if not user_id:
            return

        # 初始特征向量
        features = {
            "rage_clicks": 1 if event_type == "rage_click" else 0,
            "policy_views": 1 if event_type == "check_policy" else 0,
            "cart_adds": 1 if event_type == "add_to_cart" else 0,
            "event_count": 1,
            "last_timestamp": timestamp or ""
        }
        
        yield (user_id, features)


# =============================================================================
# CombineFn: 窗口聚合
# =============================================================================
class AggregateFeaturesFn(beam.CombineFn):
    """聚合窗口内的特征"""
    def create_accumulator(self):
        return {
            "rage_clicks": 0,
            "policy_views": 0,
            "cart_adds": 0,
            "event_count": 0,
            "last_timestamp": "" 
        }

    def add_input(self, accumulator, element):
        # element 是来自 ExtractUserFeaturesFn 的特征字典
        accumulator["rage_clicks"] += element["rage_clicks"]
        accumulator["policy_views"] += element["policy_views"]
        accumulator["cart_adds"] += element["cart_adds"]
        accumulator["event_count"] += element["event_count"]
        # 更新为最新时间戳
        if element["last_timestamp"] > accumulator["last_timestamp"]:
            accumulator["last_timestamp"] = element["last_timestamp"]
        return accumulator

    def merge_accumulators(self, accumulators):
        merged = self.create_accumulator()
        for acc in accumulators:
            merged["rage_clicks"] += acc["rage_clicks"]
            merged["policy_views"] += acc["policy_views"]
            merged["cart_adds"] += acc["cart_adds"]
            merged["event_count"] += acc["event_count"]
            if acc["last_timestamp"] > merged["last_timestamp"]:
                merged["last_timestamp"] = acc["last_timestamp"]
        return merged

    def extract_output(self, accumulator):
        return accumulator


# =============================================================================
# DoFn: 格式化为 Feature Store 写入格式
# =============================================================================
class FormatForFeatureStoreFn(beam.DoFn):
    """
    格式化聚合结果为 Feature Store 写入格式
    
    输入: (user_id, aggregated_features)
    输出: {"entity_id": str, "feature_values": dict, "feature_timestamp": str}
    """
    def process(self, element, window_info=beam.DoFn.WindowParam):
        user_id, features = element
        
        # 窗口结束时间作为特征有效时间
        feature_timestamp = window_info.end.to_utc_datetime().isoformat()
        
        # 构造 Feature Store 格式
        # 特征名称与 Feature View schema 保持一致
        feature_values = {
            "realtime_clicks_5m": features["event_count"],
            "rage_clicks_5m": features["rage_clicks"],
            "policy_views_5m": features["policy_views"],
            "cart_additions_5m": features["cart_adds"],
            # 会话时长估算 (实际应使用 SessionWindow)
            "active_session_duration": float(features["event_count"] * 10.5),
        }
        
        yield {
            "entity_id": str(user_id),
            "feature_values": feature_values,
            "feature_timestamp": feature_timestamp,
            "last_event_timestamp": features["last_timestamp"]
        }


# =============================================================================
# DoFn: 写入 Vertex AI Feature Store (带重试和错误处理)
# =============================================================================
class WriteToFeatureStoreFn(beam.DoFn):
    """
    批量写入 Vertex AI Feature Store Online Store
    
    特性:
    - 使用 FeatureOnlineStoreAdminServiceClient
    - 指数退避重试 (最多 3 次)
    - 失败记录输出到 Dead Letter 分支
    """
    
    # 定义输出标签
    DEAD_LETTER_TAG = "dead_letter"
    
    def __init__(self, project_id: str, location: str, 
                 feature_online_store: str, feature_view: str):
        self.project_id = project_id
        self.location = location
        self.feature_online_store = feature_online_store
        self.feature_view = feature_view
        self._client = None
        
    def setup(self):
        """初始化 Feature Store 客户端 (Worker 启动时调用)"""
        if FEATURE_STORE_AVAILABLE and FeatureOnlineStoreAdminServiceClient:
            try:
                client_options = {"api_endpoint": f"{self.location}-aiplatform.googleapis.com"}
                self._client = FeatureOnlineStoreAdminServiceClient(client_options=client_options)
                logging.info(f"Feature Store 客户端初始化成功: {self.feature_online_store}")
            except Exception as e:
                logging.error(f"Feature Store 客户端初始化失败: {e}")
                self._client = None
        else:
            logging.warning("Feature Store SDK 不可用，写入将降级为日志输出")
            self._client = None
    
    def _build_feature_view_path(self) -> str:
        """构造 Feature View 资源路径"""
        return (
            f"projects/{self.project_id}/locations/{self.location}/"
            f"featureOnlineStores/{self.feature_online_store}/"
            f"featureViews/{self.feature_view}"
        )
    
    def _convert_to_feature_value(self, key: str, value: Any) -> Optional[FeatureValue]:
        """将 Python 值转换为 FeatureValue protobuf"""
        if FeatureValue is None:
            return None
            
        if isinstance(value, int):
            return FeatureValue(int64_value=value)
        elif isinstance(value, float):
            return FeatureValue(double_value=value)
        elif isinstance(value, str):
            return FeatureValue(string_value=value)
        elif isinstance(value, bool):
            return FeatureValue(bool_value=value)
        else:
            logging.warning(f"不支持的特征值类型 {key}: {type(value)}")
            return FeatureValue(string_value=str(value))
    
    def _write_with_retry(self, records: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        执行写入并重试
        
        Returns:
            (成功记录列表, 失败记录列表)
        """
        if not self._client or not FEATURE_STORE_AVAILABLE:
            # 降级模式: 记录到日志
            for record in records:
                logging.info(f"[降级模式] 写入特征: entity_id={record['entity_id']}, "
                           f"features={record['feature_values']}")
            return records, []
        
        feature_view_path = self._build_feature_view_path()
        succeeded = []
        failed = []
        
        for record in records:
            entity_id = record["entity_id"]
            feature_values = record["feature_values"]
            
            # 构造写入 payload
            try:
                feature_value_map = {}
                for key, value in feature_values.items():
                    fv = self._convert_to_feature_value(key, value)
                    if fv:
                        feature_value_map[key] = fv
                
                payload = WriteFeatureValuesPayload(
                    entity_id=entity_id,
                    feature_values=feature_value_map
                )
                
                request = WriteFeatureValuesRequest(
                    feature_view=feature_view_path,
                    payloads=[payload]
                )
                
                # 带重试的写入
                last_error = None
                for attempt in range(MAX_RETRIES):
                    try:
                        self._client.write_feature_values(request=request)
                        succeeded.append(record)
                        break
                    except Exception as e:
                        last_error = e
                        delay = RETRY_BASE_DELAY * (2 ** attempt)
                        logging.warning(f"写入 Feature Store 失败 (尝试 {attempt + 1}/{MAX_RETRIES}): "
                                       f"entity_id={entity_id}, error={e}, 将在 {delay}s 后重试")
                        time.sleep(delay)
                else:
                    # 所有重试都失败
                    logging.error(f"写入 Feature Store 最终失败: entity_id={entity_id}, "
                                 f"error={last_error}")
                    record["error"] = str(last_error)
                    record["failed_at"] = datetime.utcnow().isoformat()
                    failed.append(record)
                    
            except Exception as e:
                logging.error(f"构造写入请求失败: entity_id={entity_id}, error={e}")
                record["error"] = str(e)
                record["failed_at"] = datetime.utcnow().isoformat()
                failed.append(record)
        
        return succeeded, failed
    
    def process(self, element):
        """
        处理单个记录
        
        对于流式 Pipeline，这里可以考虑使用 GroupIntoBatches 在上游批处理
        """
        succeeded, failed = self._write_with_retry([element])
        
        # 输出成功记录 (可选，用于监控)
        for record in succeeded:
            yield record
        
        # 输出失败记录到 Dead Letter 分支
        for record in failed:
            yield pvalue.TaggedOutput(self.DEAD_LETTER_TAG, record)


# =============================================================================
# DoFn: Dead Letter Queue 日志记录
# =============================================================================
class LogFailedRecordsFn(beam.DoFn):
    """
    记录写入失败的记录
    
    在生产环境中，可扩展为:
    - 写入 BigQuery dead_letter 表
    - 发送告警到 Pub/Sub
    - 触发 Cloud Monitoring 指标
    """
    def process(self, element):
        logging.error(f"[Dead Letter] 写入失败记录: "
                     f"entity_id={element.get('entity_id')}, "
                     f"error={element.get('error')}, "
                     f"failed_at={element.get('failed_at')}")
        
        # 可扩展: 将失败记录写入 BigQuery 或其他存储
        # 这里仅作为占位符输出日志
        yield element


# =============================================================================
# 主运行函数
# =============================================================================
def run(argv=None):
    """Pipeline 主入口"""
    parser = argparse.ArgumentParser(description="SentinEL Streaming Pipeline - Feature Store Sink")
    
    # 基础配置
    parser.add_argument("--input_subscription", required=True, 
                       help="Pub/Sub 订阅路径 (如 projects/PROJECT/subscriptions/SUB)")
    parser.add_argument("--project", required=True, help="GCP 项目 ID")
    parser.add_argument("--region", default="us-central1", help="GCP 区域")
    
    # Feature Store 配置
    parser.add_argument("--feature_online_store", default=DEFAULT_FEATURE_ONLINE_STORE,
                       help="Feature Online Store 名称")
    parser.add_argument("--feature_view", default=DEFAULT_FEATURE_VIEW,
                       help="Feature View 名称")
    
    known_args, pipeline_args = parser.parse_known_args(argv)
    
    # 设置 Pipeline Options
    options = PipelineOptions(pipeline_args)
    options.view_as(StandardOptions).streaming = True
    options.view_as(GoogleCloudOptions).project = known_args.project
    options.view_as(GoogleCloudOptions).region = known_args.region
    
    logging.info(f"启动 Streaming Pipeline:")
    logging.info(f"  - Project: {known_args.project}")
    logging.info(f"  - Region: {known_args.region}")
    logging.info(f"  - Feature Store: {known_args.feature_online_store}/{known_args.feature_view}")
    logging.info(f"  - Input: {known_args.input_subscription}")

    with beam.Pipeline(options=options) as p:
        # 读取并聚合
        aggregated = (
            p
            | "ReadFromPubSub" >> beam.io.ReadFromPubSub(
                subscription=known_args.input_subscription
            )
            | "ParseEvents" >> beam.ParDo(ParseEventFn())
            | "ExtractFeatures" >> beam.ParDo(ExtractUserFeaturesFn())
            | "WindowInto5Min" >> beam.WindowInto(
                window.SlidingWindows(size=300, period=60)  # 5分钟窗口，每1分钟滑动
            )
            | "AggregateByUser" >> beam.CombinePerKey(AggregateFeaturesFn())
            | "FormatForFeatureStore" >> beam.ParDo(FormatForFeatureStoreFn())
        )
        
        # 写入 Feature Store (带 Dead Letter 处理)
        write_results = (
            aggregated
            | "WriteToFeatureStore" >> beam.ParDo(
                WriteToFeatureStoreFn(
                    project_id=known_args.project,
                    location=known_args.region,
                    feature_online_store=known_args.feature_online_store,
                    feature_view=known_args.feature_view
                )
            ).with_outputs(WriteToFeatureStoreFn.DEAD_LETTER_TAG, main="success")
        )
        
        # 处理 Dead Letter 记录
        _ = (
            write_results[WriteToFeatureStoreFn.DEAD_LETTER_TAG]
            | "LogFailedRecords" >> beam.ParDo(LogFailedRecordsFn())
        )
        
        # 可选: 监控成功写入数量
        # _ = write_results.success | "CountSuccess" >> beam.combiners.Count.Globally()


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    run()
