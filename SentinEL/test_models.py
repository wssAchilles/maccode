
import vertexai
from vertexai.generative_models import GenerativeModel
import os
import google.auth

PROJECT_ID = "sentinel-ai-project-482208"

# Prioritize the "top tier" models as requested by the user
models_to_test = [
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-pro-002",
    "gemini-1.5-pro",
    "gemini-1.5-flash-001",
    "gemini-1.5-flash",
    "gemini-1.5-pro-001",
    "gemini-1.0-pro-001",
    "gemini-1.0-pro",
    "gemini-pro"
]

regions_to_test = ["us-central1", "us-west1", "us-east4", "asia-northeast1", "europe-west4"]

print("Starting model availability test across regions...")
print(f"Target Project: {PROJECT_ID}")

# Diagnosis info
try:
    creds, project = google.auth.default()
    print(f"Current Auth Project: {project}")
    if hasattr(creds, 'service_account_email'):
        print(f"Service Account: {creds.service_account_email}")
except Exception as e:
    print(f"Auth check warning: {e}")

print("-" * 30)

for region in regions_to_test:
    print(f"\n--- Testing Region: {region} ---")
    try:
        vertexai.init(project=PROJECT_ID, location=region)
    except Exception as e:
        print(f"Failed to init vertexai in {region}: {e}")
        continue

    for model_name in models_to_test:
        print(f"Testing model: {model_name} ...", end=" ", flush=True)
        try:
            model = GenerativeModel(model_name)
            # Try a simple generation to confirm real access
            response = model.generate_content("Hello")
            print(f"SUCCESS! ")
            print(f"\n!!! FOUND WORKING CONFIGURATION !!!")
            print(f"Region: {region}")
            print(f"Model: {model_name}")
            print("-" * 30)
            exit(0) # Exit immediately on success
        except Exception as e:
            print(f"FAILED.")
            # Only print error for the top model to check specific permission issues
            if model_name == "gemini-1.5-pro-002":
                 print(f"  [Debug] Error for {model_name}: {e}")

print("\nNo working model configuration found.")
