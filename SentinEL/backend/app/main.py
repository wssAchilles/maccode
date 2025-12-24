from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints import analysis
import uvicorn

# Initialize FastAPI app
app = FastAPI(
    title="SentinEL Enterprise Microservice",
    description="High-Performance Customer Retention AI Agent Backend",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# --- CORS Configuration ---
# Critical for communicating with the Frontend (localhost:3000)
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
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
    return {"status": "healthy", "service": "SentinEL Backend"}

if __name__ == "__main__":
    # In production, we'd use gunicorn or similar manager
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)
