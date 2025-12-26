
import time
import requests
import json
import sys

# Backend URL from deployment
API_URL = "https://sentinel-backend-kijag7ukkq-uc.a.run.app"
API_KEY = "sentinel_top_secret_2025"

def verify_polling():
    print(f"Testing Async Polling against {API_URL}...")
    
    # 1. Start Analysis
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }
    payload = {"user_id": "63826"}
    
    print("1. Sending /analyze request...")
    response = requests.post(f"{API_URL}/api/v1/analyze", headers=headers, json=payload)
    
    if response.status_code != 202:
        print(f"FAILED: Expected 202 Accepted, got {response.status_code}")
        print(response.text)
        sys.exit(1)
        
    data = response.json()
    analysis_id = data.get("analysis_id")
    print(f"SUCCESS: Job queued. Analysis ID: {analysis_id}")
    
    # 2. Poll for Results
    print("2. Polling for results...")
    attempts = 0
    max_attempts = 20
    
    while attempts < max_attempts:
        time.sleep(1)
        print(f"   Attempt {attempts+1}...", end=" ")
        
        status_res = requests.get(f"{API_URL}/api/v1/analyze/{analysis_id}", headers=headers)
        
        if status_res.status_code == 200:
            status_data = status_res.json()
            status = status_data.get("status")
            print(f"Status: {status}")
            
            if status == "COMPLETED":
                # Verify payload
                risk_level = status_data.get("risk_level")
                churn_prob = status_data.get("churn_probability")
                
                print("\nVerification Results:")
                print(f"- Status: {status}")
                print(f"- Risk Level: {risk_level}")
                print(f"- Churn Prob: {churn_prob}")
                
                if risk_level is not None and churn_prob is not None:
                    print("\n✅ API Polling Logic VERIFIED. 'NaN' error should be resolved.")
                    sys.exit(0)
                else:
                    print("\n❌ FAILED: Response missing risk_level or churn_probability")
                    sys.exit(1)
        else:
            print(f"Error checking status: {status_res.status_code}")
            
        attempts += 1
        
    print("\n❌ FAILED: Timeout waiting for completion")
    sys.exit(1)

if __name__ == "__main__":
    verify_polling()
