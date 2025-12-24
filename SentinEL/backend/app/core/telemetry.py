"""
SentinEL Telemetry Module - Google Cloud Trace 集成

使用 OpenTelemetry SDK 将分布式追踪数据发送到 Google Cloud Trace。
支持自动 FastAPI 仪表盘和手动埋点。

用法:
    from app.core.telemetry import setup_telemetry, get_tracer
    
    # 在 main.py 中初始化
    setup_telemetry(app)
    
    # 在服务中手动埋点
    tracer = get_tracer()
    with tracer.start_as_current_span("operation_name"):
        # 业务逻辑
        pass
"""

import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor


# ============================================
# 配置常量
# ============================================
SERVICE_NAME = "sentinel-backend"
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "sentinel-ai-project-482208")

# 全局 Tracer 实例
_tracer = None


def setup_telemetry(app) -> None:
    """
    初始化 OpenTelemetry 并配置 Google Cloud Trace 导出器。
    
    Args:
        app: FastAPI 应用实例
        
    功能:
    1. 配置 TracerProvider 和 Resource
    2. 配置 CloudTraceSpanExporter
    3. 自动注入 FastAPI 仪表盘
    4. 自动注入 requests 库仪表盘 (用于外部 HTTP 调用)
    """
    global _tracer
    
    # 创建资源标识 (用于在 Cloud Console 中识别服务)
    resource = Resource.create({
        "service.name": SERVICE_NAME,
        "service.version": "2.0.0",
        "cloud.provider": "gcp",
        "cloud.platform": "cloud_run",
        "cloud.account.id": PROJECT_ID,
    })
    
    # 创建 TracerProvider
    provider = TracerProvider(resource=resource)
    
    # 配置 Cloud Trace 导出器
    # 在 Cloud Run 上会自动使用服务账号认证
    try:
        exporter = CloudTraceSpanExporter(project_id=PROJECT_ID)
        
        # 使用 BatchSpanProcessor 批量发送 (提高性能)
        span_processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(span_processor)
        
        print(f"[Telemetry] Cloud Trace exporter configured for project: {PROJECT_ID}")
    except Exception as e:
        print(f"[Telemetry] Warning: Failed to configure Cloud Trace exporter: {e}")
        print("[Telemetry] Traces will be logged locally only.")
    
    # 设置全局 TracerProvider
    trace.set_tracer_provider(provider)
    
    # 获取 Tracer 实例
    _tracer = trace.get_tracer(__name__)
    
    # 自动注入 FastAPI 仪表盘
    # 这会自动为每个 HTTP 请求创建 span
    FastAPIInstrumentor.instrument_app(app)
    print("[Telemetry] FastAPI auto-instrumentation enabled.")
    
    # 自动注入 requests 库 (用于追踪外部 HTTP 调用)
    RequestsInstrumentor().instrument()
    print("[Telemetry] Requests library auto-instrumentation enabled.")
    
    print(f"[Telemetry] OpenTelemetry initialized for service: {SERVICE_NAME}")


def get_tracer() -> trace.Tracer:
    """
    获取全局 Tracer 实例用于手动埋点。
    
    Returns:
        OpenTelemetry Tracer 实例
        
    用法:
        tracer = get_tracer()
        with tracer.start_as_current_span("my_operation") as span:
            span.set_attribute("key", "value")
            # 业务逻辑
    """
    global _tracer
    if _tracer is None:
        # 如果未初始化，返回默认 tracer (不会发送到 Cloud Trace)
        _tracer = trace.get_tracer(__name__)
    return _tracer
