import subprocess
import time
import requests
import sys
import os
import signal

def verify_system():
    print("Starting system verification...")
    
    # Start the Flask app in a separate process
    # Assuming main.py runs the app
    process = subprocess.Popen(
        [sys.executable, "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=dict(os.environ, PORT="8080")  # Set PORT to 8080
    )
    
    print("Waiting for server to start (10s)...")
    time.sleep(10)
    
    base_url = "http://localhost:8080"
    success = True
    
    try:
        # 1. Health/Root Check
        print(f"Checking {base_url}/...")
        try:
            resp = requests.get(f"{base_url}/", timeout=5)
            if resp.status_code == 200:
                print("✅ Root endpoint accessible")
            else:
                print(f"❌ Root endpoint failed: {resp.status_code}")
                success = False
        except Exception as e:
            print(f"❌ Root endpoint connection failed: {e}")
            success = False

        # 2. API Health Check (if exists) or just another endpoint
        # Trying a known endpoint like /api/analysis or /api/ml/explain (GET might fail but 405 is better than 404)
        endpoints = [
            ("/api/ml/explain", "POST"), # Expecting 400 or 415 if no data, but 404 means route missing
            ("/api/rag/ask", "POST"),
        ]
        
        for ep, method in endpoints:
            print(f"Checking availability of {ep}...")
            try:
                if method == "POST":
                    resp = requests.post(f"{base_url}{ep}", json={}, timeout=5)
                else:
                    resp = requests.get(f"{base_url}{ep}", timeout=5)
                
                # We expect 400 (Bad Request) or 422 (Validation Error) or 415, NOT 404
                if resp.status_code != 404:
                    print(f"✅ Endpoint {ep} is registered (Status: {resp.status_code})")
                else:
                    print(f"❌ Endpoint {ep} not found (404)")
                    success = False
            except Exception as e:
                print(f"❌ Endpoint {ep} check failed: {e}")
                success = False

    finally:
        print("Stopping server...")
        try:
            os.kill(process.pid, signal.SIGTERM)
            process.wait(timeout=5)
        except:
            process.kill()
            
    if success:
        print("\n✅ System Integration Verification Passed!")
        sys.exit(0)
    else:
        print("\n❌ System Integration Verification FAILED")
        sys.exit(1)

if __name__ == "__main__":
    verify_system()
