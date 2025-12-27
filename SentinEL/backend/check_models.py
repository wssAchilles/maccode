import vertexai
from vertexai.generative_models import GenerativeModel
import os

project_id = "sentinel-ai-project-482208"
location = "us-central1"

print(f"Initializing Vertex AI with project={project_id}, location={location}")
vertexai.init(project=project_id, location=location)

def test_gen_model(name):
    print(f"Testing GenerativeModel: {name} ...")
    try:
        model = GenerativeModel(name)
        # Check if we can get a response
        response = model.generate_content("Hello")
        print(f"SUCCESS: {name}")
        return True
    except Exception as e:
        print(f"FAILED: {name} - {e}")
        return False

# Test the user-specified model
test_gen_model("gemini-2.5-pro")

# Fallback check
test_gen_model("gemini-1.5-pro-001")
