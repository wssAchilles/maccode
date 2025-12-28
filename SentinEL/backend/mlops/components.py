from kfp import dsl
from typing import NamedTuple

@dsl.component(base_image="python:3.9", packages_to_install=["google-cloud-bigquery", "pandas"])
def extract_data_op(
    project_id: str,
    dataset_id: str,
    table_id: str,
    lookback_days: int = 30
) -> str:
    """
    Extracts the latest training data from BigQuery and exports to GCS or passes metadata.
    For this 'mock' enterprise pipeline, we return a GCS URI string.
    """
    import logging
    
    logging.getLogger().setLevel(logging.INFO)
    logging.info(f"Extracting data from {project_id}.{dataset_id}.{table_id} (Last {lookback_days} days)")
    
    # In a real scenario, we would run a BQ Extract Job here.
    # For now, we simulate finding a dataset.
    data_uri = f"gs://sentinel-mlops-artifacts-{project_id}/training_data/churn_data_latest.csv"
    
    logging.info(f"Data exported to: {data_uri}")
    return data_uri

@dsl.component(base_image="python:3.9", packages_to_install=["scikit-learn", "pandas"])
def train_model_op(
    training_data_uri: str,
    epochs: int = 10,
    learning_rate: float = 0.01
) -> NamedTuple("ModelOutput", [("model_uri", str), ("metrics", dict)]):
    """
    Simulates training a PyTorch/TensorFlow model.
    Returns the model artifact URI and training metrics.
    """
    import time
    import random
    import logging
    from collections import namedtuple
    
    logging.getLogger().setLevel(logging.INFO)
    logging.info(f"Starting training with data: {training_data_uri}")
    logging.info(f"Hyperparams: epochs={epochs}, lr={learning_rate}")
    
    # Simulate Training Delay
    time.sleep(5)
    
    # Simulate finding a 'better' model occasionally
    accuracy = 0.85 + (random.random() * 0.1) # 0.85 - 0.95
    loss = 1.0 - accuracy
    
    model_uri = f"gs://sentinel-models/churn_model/v_{int(time.time())}"
    metrics = {"accuracy": accuracy, "loss": loss}
    
    logging.info(f"Training complete. Metrics: {metrics}")
    logging.info(f"Model saved to: {model_uri}")
    
    model_output = namedtuple("ModelOutput", ["model_uri", "metrics"])
    return model_output(model_uri, metrics)

@dsl.component(base_image="python:3.9")
def evaluate_model_op(
    new_model_metrics: dict,
    baseline_accuracy: float = 0.80
) -> str:
    """
    Compares the new model against a baseline or currently deployed model.
    Returns 'pass' or 'fail'.
    """
    import logging
    
    logging.getLogger().setLevel(logging.INFO)
    new_acc = new_model_metrics.get("accuracy", 0.0)
    
    logging.info(f"Evaluating new model (acc={new_acc:.4f}) vs baseline ({baseline_accuracy})")
    
    if new_acc > baseline_accuracy:
        logging.info("Evaluation PASSED. New model is better.")
        return "pass"
    else:
        logging.info("Evaluation FAILED. New model is not better.")
        return "fail"

@dsl.component(base_image="python:3.9", packages_to_install=["google-cloud-aiplatform"])
def deploy_model_op(
    model_uri: str,
    project_id: str,
    region: str,
    endpoint_name: str
) -> str:
    """
    Deploys the validated model to Vertex AI Endpoint.
    """
    import logging
    import time
    
    logging.getLogger().setLevel(logging.INFO)
    logging.info(f"Deploying model {model_uri} to Endpoint {endpoint_name} in {region}...")
    
    # Simulate Deployment Delay
    time.sleep(3)
    
    deploy_status = "deployed" 
    logging.info(f"Deployment successful. Status: {deploy_status}")
    
    return deploy_status
