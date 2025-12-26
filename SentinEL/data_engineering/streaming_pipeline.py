"""
SentinEL 实时流式计算管道 (Streaming Pipeline)

功能:
    1. 从 Google Cloud Pub/Sub 读取点击流事件 (JSON)
    2. 应用固定窗口 (Fixed/Sliding Windows) 进行聚合计算
    3. 解析用户行为特征 (如 rage_click 次数, policy_views)
    4. 将聚合后的特征写入 Vertex AI Feature Store (Feature Group 对应的 BigQuery 表)
       注意: Feature Store Online Storage 会自动从 BigQuery 同步 (Feature View sync)

运行方式:
    python data_engineering/streaming_pipeline.py \
        --project YOUR_PROJECT_ID \
        --region us-central1 \
        --input_subscription projects/YOUR_PROJECT_ID/subscriptions/sentinel-clickstream-sub \
        --runner DataflowRunner \
        --job_name sentinel-streaming-features

依赖:
    pip install apache-beam[gcp]
"""

import argparse
import json
import logging
from datetime import datetime

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions, GoogleCloudOptions
from apache_beam import window

# =============================================================================
# 配置常量
# =============================================================================
BIGQUERY_TABLE = "user_realtime_aggregates"
BIGQUERY_DATASET = "sentinel_features"

class ParseEventFn(beam.DoFn):
    """解析 JSON 事件并添加处理时间戳"""
    def process(self, element):
        try:
            event = json.loads(element.decode("utf-8"))
            yield event
        except Exception as e:
            logging.error(f"Failed to parse event: {e}")

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
            "last_timestamp": timestamp
        }
        
        yield (user_id, features)

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
        # element is specific feature dict from ExtractUserFeaturesFn
        accumulator["rage_clicks"] += element["rage_clicks"]
        accumulator["policy_views"] += element["policy_views"]
        accumulator["cart_adds"] += element["cart_adds"]
        accumulator["event_count"] += element["event_count"]
        # Update timestamp to latest
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

class FormatForBigQueryFn(beam.DoFn):
    """格式化为 BigQuery 表结构 (Feature Store Source)"""
    def process(self, element, window=beam.DoFn.WindowParam):
        user_id, features = element
        
        # 窗口结束时间作为特征有效时间
        feature_timestamp = window.end.to_utc_datetime().isoformat()
        
        row = {
            "entity_id": str(user_id),
            "feature_timestamp": feature_timestamp,
            "realtime_clicks_5m": features["event_count"],
            "rage_clicks_5m": features["rage_clicks"],
            "policy_views_5m": features["policy_views"],
            "cart_additions_5m": features["cart_adds"],
            # 简单模拟 active_session_duration, 实际需要 SessionWindow
            "active_session_duration": float(features["event_count"] * 10.5), 
            "last_event_timestamp": features["last_timestamp"]
        }
        
        yield row

def run(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_subscription", required=True, help="Pub/Sub subscription to read from")
    parser.add_argument("--project", required=True, help="GCP Project ID")
    parser.add_argument("--region", default="us-central1", help="GCP Region")
    
    known_args, pipeline_args = parser.parse_known_args(argv)
    
    # 设置 Pipeline Options
    options = PipelineOptions(pipeline_args)
    options.view_as(StandardOptions).streaming = True
    options.view_as(GoogleCloudOptions).project = known_args.project
    options.view_as(GoogleCloudOptions).region = known_args.region
    
    output_table = f"{known_args.project}:{BIGQUERY_DATASET}.{BIGQUERY_TABLE}"

    with beam.Pipeline(options=options) as p:
        (
            p
            | "ReadFromPubSub" >> beam.io.ReadFromPubSub(subscription=known_args.input_subscription)
            | "ParseEvents" >> beam.ParDo(ParseEventFn())
            | "ExtractFeatures" >> beam.ParDo(ExtractUserFeaturesFn())
            | "WindowInto5Min" >> beam.WindowInto(window.SlidingWindows(size=300, period=60)) # 5分钟窗口，每1分钟滑动更新
            | "AggregateByUser" >> beam.CombinePerKey(AggregateFeaturesFn())
            | "FormatForBQ" >> beam.ParDo(FormatForBigQueryFn())
            | "WriteToBigQuery" >> beam.io.WriteToBigQuery(
                output_table,
                schema="entity_id:STRING,feature_timestamp:TIMESTAMP,realtime_clicks_5m:INTEGER,rage_clicks_5m:INTEGER,policy_views_5m:INTEGER,cart_additions_5m:INTEGER,active_session_duration:FLOAT,last_event_timestamp:TIMESTAMP",
                write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
                create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED
            )
        )

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    run()
