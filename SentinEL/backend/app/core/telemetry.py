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

# Try to import OpenTelemetry, provide dummy implementations if missing
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    _HAS_OPENTELEMETRY = True
except ImportError:
    _HAS_OPENTELEMETRY = False
    trace = None

# ============================================
# 配置常量
# ============================================
SERVICE_NAME = "sentinel-backend"
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "sentinel-ai-project-482208")

# 全局 Tracer 实例
_tracer = None


class DummyTracer:
    def start_as_current_span(self, name):
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def set_attribute(self, key, value):
        pass


def setup_telemetry(app) -> None:
    """
    初始化 OpenTelemetry 并配置 Google Cloud Trace 导出器。
    如果依赖缺失，则跳过初始化。
    """
    global _tracer
    
    if not _HAS_OPENTELEMETRY:
        print("[Telemetry] OpenTelemetry packages not found. Telemetry disabled.")
        _tracer = DummyTracer()
        return

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


def get_tracer():
    """
    获取全局 Tracer 实例用于手动埋点。
    """
    global _tracer
    if _tracer is None:
        if _HAS_OPENTELEMETRY:
             _tracer = trace.get_tracer(__name__)
        else:
             _tracer = DummyTracer()
             
    return _tracer
