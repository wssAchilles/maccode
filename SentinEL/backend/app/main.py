"""
SentinEL Enterprise Microservice

高性能客户留存 AI Agent 后端
集成 Google Cloud Trace 全链路追踪
"""

import sys
import os
print("DEBUG: sys.path:", sys.path)
try:
    print("DEBUG: site-packages contents:", os.listdir("/usr/local/lib/python3.11/site-packages"))
except Exception as e:
    print("DEBUG: Could not list site-packages:", e)

from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints import analysis, pipeline, mlops

app = FastAPI(
    title="SentinEL Backend",
    description="High-performance AI Agent Backend",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Telemetry (Optional)
from app.core.telemetry import setup_telemetry
setup_telemetry(app)

# --- Register Routers ---
app.include_router(analysis.router, prefix="/api/v1", tags=["Analysis"])
app.include_router(pipeline.router, prefix="/api/v1", tags=["Data Pipeline"])
app.include_router(mlops.router, prefix="/api/v1", tags=["MLOps"])

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "SentinEL Backend", "tracing": "enabled"}

if __name__ == "__main__":
    # In production, we'd use gunicorn or similar manager
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)

