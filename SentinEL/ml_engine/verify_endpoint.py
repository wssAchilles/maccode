
from google.cloud import aiplatform
import google.auth
import json

# Configuration
PROJECT_ID = "sentinel-ai-project-482208"
LOCATION = "us-central1"
ENDPOINT_ID = "8203956532627374080"

def predict_custom_trained_model_sample(
    project: str,
    endpoint_id: str,
    instances: list,
    location: str = "us-central1",
    api_endpoint: str = "us-central1-aiplatform.googleapis.com",
):
    # The AI Platform services require regional API endpoints.
    client_options = {"api_endpoint": api_endpoint}
    # Initialize client that will be used to create and send requests.
    # This client only needs to be created once, and can be reused for multiple requests.
    client = aiplatform.gapic.PredictionServiceClient(client_options=client_options)

    # The format of each instance should conform to the deployed model's prediction input schema.
    encoded_instances = []
    for instance in instances:
        encoded_instances.append(instance)

    endpoint = client.endpoint_path(
        project=project, location=location, endpoint=endpoint_id
    )

    response = client.predict(
        endpoint=endpoint, instances=encoded_instances
    )

    print("response")
    print(" deployed_model_id:", response.deployed_model_id)
    print(" predictions:", response.predictions)

if __name__ == "__main__":
    # Load test request
    with open("ml_engine/test_request.json", "r") as f:
        data = json.load(f)
        instances = data["instances"]
    
    print(f"Sending request to endpoint {ENDPOINT_ID} in {LOCATION}...")
    predict_custom_trained_model_sample(
        project=PROJECT_ID,
        endpoint_id=ENDPOINT_ID,
        location=LOCATION,
        instances=instances
    )
