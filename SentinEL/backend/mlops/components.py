from kfp.dsl import component, Input, Output, Artifact, Model, Metrics

@component(base_image="python:3.9", packages_to_install=["google-cloud-bigquery", "pandas"])
def data_extraction_op(
    project_id: str,
    dataset_id: str,
    table_id: str,
    dataset: Output[Artifact]
):
    """
    Simulates extracting data from BigQuery for training.
    In a real scenario, this would export BQ table to GCS CSV/Avro.
    """
    import time
    import logging
    
    logging.info(f"Extracting data from {project_id}.{dataset_id}.{table_id}...")
    
    # Simulate data extraction time
    time.sleep(2)
    
    # Write a dummy path/manifest to the artifact output
    dataset.path = f"gs://{project_id}-data-bucket/churn_data/v1/train.csv"
    logging.info(f"Data extracted to {dataset.path}")

@component(base_image="python:3.9", packages_to_install=["scikit-learn", "pandas"])
def model_training_op(
    dataset: Input[Artifact],
    model: Output[Model],
    metrics: Output[Metrics]
):
    """
    Simulates model training and returns metrics.
    """
    import time
    import random
    import logging
    
    logging.info(f"Training model using data from {dataset.path}...")
    
    # Simulate training time
    time.sleep(5)
    
    # Generate dummy metrics
    accuracy = 0.70 + (random.random() * 0.20)  # Random accuracy between 0.70 and 0.90
    loss = 0.5 - (accuracy * 0.4)
    
    logging.info(f"Training complete. Accuracy: {accuracy:.4f}, Loss: {loss:.4f}")
    
    # Log metrics
    metrics.log_metric("accuracy", accuracy)
    metrics.log_metric("loss", loss)
    
    # Save a dummy model file
    model.path = f"{model.path}/model.joblib"
    with open(model.path, "w") as f:
        f.write("dummy model content")

@component(base_image="python:3.9")
def model_evaluation_op(
    metrics: Input[Metrics],
    threshold: float = 0.75
) -> str:
    """
    Evaluates model metrics against a threshold.
    Returns "true" if model should be deployed, "false" otherwise.
    """
    import logging
    
    accuracy = metrics.metadata.get("accuracy", 0.0)
    logging.info(f"Evaluating model. Accuracy: {accuracy}, Threshold: {threshold}")
    
    if accuracy >= threshold:
        logging.info("Model passed evaluation.")
        return "true"
    else:
        logging.info("Model failed evaluation.")
        return "false"

@component(base_image="python:3.9", packages_to_install=["google-cloud-aiplatform"])
def model_deployment_op(
    model: Input[Model],
    project_id: str,
    region: str,
    serving_container_image_uri: str
):
    """
    Simulates deploying the model to Vertex AI Endpoint.
    """
    import time
    import logging
    # import google.cloud.aiplatform as aiplatform # Uncomment for real usage
    
    logging.info(f"Deploying model from {model.path} to Vertex AI...")
    logging.info(f"Project: {project_id}, Region: {region}")
    
    # Simulate deployment
    # aiplatform.init(project=project_id, location=region)
    # Model registry upload and endpoint deployment logic would go here
    
    time.sleep(3)
    
    logging.info("Model successfully deployed to Endpoint: sentinel-churn-prediction-v2")
