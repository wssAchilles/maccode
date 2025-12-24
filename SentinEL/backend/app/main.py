"""
SentinEL Enterprise Microservice

高性能客户留存 AI Agent 后端
集成 Google Cloud Trace 全链路追踪
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints import analysis
from app.core.telemetry import setup_telemetry
import uvicorn

# Initialize FastAPI app
app = FastAPI(
    title="SentinEL Enterprise Microservice",
    description="High-Performance Customer Retention AI Agent Backend",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# --- 初始化 OpenTelemetry (Google Cloud Trace) ---
setup_telemetry(app)

# --- CORS Configuration ---
# Critical for communicating with the Frontend (local + Cloud Run)
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    # Cloud Run 生产环境
    "https://sentinel-frontend-kijag7ukkq-uc.a.run.app",
    "https://sentinel-frontend-672705370432.us-central1.run.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Register Routers ---
app.include_router(analysis.router, prefix="/api/v1", tags=["Analysis"])

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "SentinEL Backend", "tracing": "enabled"}

if __name__ == "__main__":
    # In production, we'd use gunicorn or similar manager
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)

