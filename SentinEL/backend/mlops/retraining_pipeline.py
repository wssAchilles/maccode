from kfp import dsl
from kfp import compiler
import os
import sys

# Add backend directory to path to import components
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from mlops.components import extract_data_op, train_model_op, evaluate_model_op, deploy_model_op

PIPELINE_ROOT = "gs://sentinel-mlops-artifacts-sentinel-ai-project-482208/pipeline_root_retrain"

@dsl.pipeline(
    name="sentinel-churn-retraining-pipeline",
    description="Automated pipeline to retrain and deploy the churn prediction model.",
    pipeline_root=PIPELINE_ROOT
)
def retraining_pipeline(
    project_id: str = "sentinel-ai-project-482208",
    region: str = "us-central1",
    dataset_id: str = "sentinel_analytics",
    table_id: str = "user_behavior_logs",
    lookback_days: int = 30,
    epochs: int = 15,
    baseline_accuracy: float = 0.82
):
    # Step 1: Data Extraction
    extract_task = extract_data_op(
        project_id=project_id,
        dataset_id=dataset_id,
        table_id=table_id,
        lookback_days=lookback_days
    ).set_display_name("Extract Training Data")
    
    # Step 2: Training (Simulation)
    train_task = train_model_op(
        training_data_uri=extract_task.output,
        epochs=epochs
    ).set_display_name("Train PyTorch Model")
    
    # Step 3: Evaluation
    eval_task = evaluate_model_op(
        new_model_metrics=train_task.outputs["metrics"],
        baseline_accuracy=baseline_accuracy
    ).set_display_name("Evaluate Model Quality")
    
    # Step 4: Conditional Deployment
    with dsl.Condition(
        eval_task.output == "pass",
        name="deploy-condition"
    ):
        deploy_task = deploy_model_op(
            model_uri=train_task.outputs["model_uri"],
            project_id=project_id,
            region=region,
            endpoint_name="sentinel-churn-endpoint"
        ).set_display_name("Deploy to Vertex AI")

if __name__ == "__main__":
    output_file = "sentinel_retraining_pipeline.json"
    print(f"Compiling retraining pipeline to {output_file}...")
    compiler.Compiler().compile(
        pipeline_func=retraining_pipeline,
        package_path=output_file
    )
    print("Compilation complete.")
