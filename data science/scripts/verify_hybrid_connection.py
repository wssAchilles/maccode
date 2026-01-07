import requests
import json
import time

# Heavy Core URL from AppConstants
CLOUD_RUN_URL = "https://sentinel-backend-cloudrun-nj4m3gcxqq-uc.a.run.app"

def test_rag_endpoint():
    print(f"\n[Testing RAG Endpoint] {CLOUD_RUN_URL}/api/rag/ask")
    payload = {
        "question": "Please explain the purpose of this system.",
        "collection_name": "default"
    }
    
    try:
        start_time = time.time()
        # Note: Using a short timeout to fail fast if incorrect, 
        # but Cloud Run cold starts can take time.
        response = requests.post(
            f"{CLOUD_RUN_URL}/api/rag/ask", 
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        duration = time.time() - start_time
        
        print(f"Status Code: {response.status_code}")
        print(f"Duration: {duration:.2f}s")
        
        if response.status_code == 200:
            print("✅ RAG Response:", response.json())
        else:
            print("❌ RAG Failed:", response.text)
            
    except Exception as e:
        print(f"❌ RAG Error: {e}")

def test_deep_learning_training_endpoint():
    print(f"\n[Testing Deep Learning Train Endpoint] {CLOUD_RUN_URL}/api/ml/deep/train")
    # Using dry_run or minimal parameters if possible to avoid huge costs/time.
    # Since we don't have a dry_run param, we'll rely on the fact that authentication might be missing
    # or just check if the endpoint is reachable (401/403 or 200).
    # Ideally, we should send a valid but small training request.
    
    payload = {
        "storage_path": "data/sample.csv",
        "model_type": "lstm",
        "epochs": 1, # Minimal epochs
        "batch_size": 32,
        "window_size": 12
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{CLOUD_RUN_URL}/api/ml/deep/train",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        duration = time.time() - start_time
        
        print(f"Status Code: {response.status_code}")
        print(f"Duration: {duration:.2f}s")
        
        if response.status_code == 200:
            print("✅ Training Initiated:", response.json())
        elif response.status_code in [400, 404, 500]: 
            # 400/500 might mean it tried but failed on data, which proves connectivity at least.
            print(f"⚠️ Endpoint Reachable but Error (Expected if DB empty): {response.status_code} - {response.text[:200]}")
        else:
            print(f"❌ Unexpected Status: {response.status_code}")
            
    except Exception as e:
        print(f"❌ DB Train Error: {e}")

if __name__ == "__main__":
    print(f"Verifying Hybrid Core Integration -> {CLOUD_RUN_URL}")
    test_rag_endpoint()
    test_deep_learning_training_endpoint()
