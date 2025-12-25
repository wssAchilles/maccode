from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
import os
import logging

API_KEY_NAME = "X-API-KEY"
# In a real scenario, use os.getenv("API_SECRET_KEY")
# For this demo, we hardcode as requested
API_SECRET_KEY = "sentinel_top_secret_2025" 

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

logger = logging.getLogger(__name__)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key == API_SECRET_KEY:
        return api_key
    
    logger.warning(f"Unauthorized access attempt with key: {api_key}")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Could not validate API KEY"
    )
