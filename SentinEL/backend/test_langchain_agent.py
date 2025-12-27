
import os
import logging
from langchain_google_vertexai import ChatVertexAI
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_langchain_gemini():
    print(f"Testing ChatVertexAI with model: gemini-1.5-flash-001")
    try:
        llm = ChatVertexAI(
            project=settings.PROJECT_ID,
            location=settings.LOCATION,
            model_name="gemini-1.5-flash-001",
            temperature=0.0,
            max_output_tokens=1024,
        )
        
        response = llm.invoke("Hello, are you online? Respond with 'YES'.")
        print(f"Response: {response.content}")
        
        if "YES" in response.content:
            print("SUCCESS: ChatVertexAI is working with gemini-1.5-flash-001")
            
    except Exception as e:
        print(f"FAILED: ChatVertexAI failed with error: {e}")

if __name__ == "__main__":
    test_langchain_gemini()
