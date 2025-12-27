"""
SentinEL Enterprise Microservice

高性能客户留存 AI Agent 后端
集成 Google Cloud Trace 全链路追踪
"""

import sys
import os
import logging

# Basic logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Debug info
try:
    print("DEBUG: sys.path:", sys.path)
    # print("DEBUG: site-packages contents:", os.listdir("/usr/local/lib/python3.11/site-packages")) # Commented out to reduce log noise
except Exception as e:
    print("DEBUG: Error checking env:", e)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

# Import Endpoints
from app.api.v1.endpoints import analysis, pipeline, mlops, events, recommendations, agent

app = FastAPI(
    title="SentinEL Backend",
    description="High-performance AI Agent Backend",
    version=settings.VERSION
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
try:
    from app.core.telemetry import setup_telemetry
    setup_telemetry(app)
except ImportError:
    logger.warning("Telemetry module not found, skipping.")

# --- Register Routers ---
app.include_router(analysis.router, prefix="/api/v1", tags=["Analysis"])
app.include_router(pipeline.router, prefix="/api/v1", tags=["Data Pipeline"])
app.include_router(mlops.router, prefix="/api/v1", tags=["MLOps"])
app.include_router(recommendations.router, prefix="/api/v1", tags=["Recommendations"])
app.include_router(agent.router, prefix="/api/v1", tags=["Agent Orchestration"])
app.include_router(events.router, prefix="/api/v1/events", tags=["Internal Events"])

# --- Health Check ---
@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "SentinEL Backend", "version": settings.VERSION}

# --- Diagnostic Endpoint ---
@app.get("/api/v1/test_llm")
async def test_llm_endpoint():
    """
    Diagnostic endpoint to test LLM connectivity and report library versions.
    """
    import sys
    import traceback
    
    debug_info = {
        "python_version": sys.version,
        "libraries": {},
        "error": None,
        "traceback": None,
        "response": None
    }
    
    # Check Library Versions
    libs_to_check = [
        "google.protobuf",
        "google.cloud.aiplatform",
        "vertexai",
        "langchain",
        "langchain_google_vertexai",
        "tensorflow"
    ]
    
    for lib in libs_to_check:
        try:
            mod = __import__(lib)
            # Handle submodules like google.protobuf
            if lib == "google.protobuf":
                mod = sys.modules["google.protobuf"]
            elif lib == "google.cloud.aiplatform":
                mod = sys.modules["google.cloud.aiplatform"]
                
            version = getattr(mod, "__version__", "unknown")
            debug_info["libraries"][lib] = version
        except ImportError:
             debug_info["libraries"][lib] = "NOT_INSTALLED"
        except Exception as e:
             debug_info["libraries"][lib] = f"ERROR: {e}"

    # Test LLM
    try:
        from langchain_google_vertexai import ChatVertexAI
        
        # Use simple prompt
        llm = ChatVertexAI(
            project=settings.PROJECT_ID,
            location=settings.LOCATION,
            model_name="gemini-2.5-pro",
            temperature=0.0
        )
        resp = llm.invoke("Hello, status check.")
        debug_info["response"] = resp.content
    except Exception as e:
        debug_info["error"] = str(e)
        debug_info["traceback"] = traceback.format_exc()
        
    return debug_info

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)
