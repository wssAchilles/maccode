import vertexai
from vertexai.generative_models import GenerativeModel
import os

project_id = "sentinel-ai-project-482208"
regions = ["us-central1", "us-west1", "us-east4", "us-west4", "northamerica-northeast1", "asia-northeast1", "europe-west4"]
model_names = ["gemini-1.5-flash-001", "gemini-1.0-pro-001"]

print(f"Testing project: {project_id}")

for loc in regions:
    print(f"\n--- Testing Region: {loc} ---")
    try:
        vertexai.init(project=project_id, location=loc)
        for m in model_names:
            print(f"Trying {m}...")
            try:
                model = GenerativeModel(m)
                response = model.generate_content("Hi")
                print(f"SUCCESS: {loc} with {m}")
                print(f"Response: {response.text}")
                exit(0) # Found one!
            except Exception as e:
                print(f"FAILED {m}: {e}")
    except Exception as e:
        print(f"FAILED Region init {loc}: {e}")
