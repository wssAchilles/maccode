from kfp import dsl
from kfp import compiler
from mlops.components import (
    data_extraction_op,
    model_training_op,
    model_evaluation_op,
    model_deployment_op
)

PIPELINE_ROOT = "gs://sentinel-ai-project-482208-pipeline-root"
PROJECT_ID = "sentinel-ai-project-482208"
REGION = "us-central1"

@dsl.pipeline(
    name="sentinel-continuous-training-pipeline",
    description="Automated retraining pipeline for Churn Prediction model",
    pipeline_root=PIPELINE_ROOT
)
def retraining_pipeline(
    project_id: str = PROJECT_ID,
    region: str = REGION,
    dataset_id: str = "retail_ai",
    table_id: str = "user_features_training",
    accuracy_threshold: float = 0.75
):
    # 1. Data Extraction
    extraction_task = data_extraction_op(
        project_id=project_id,
        dataset_id=dataset_id,
        table_id=table_id
    )
    
    # 2. Model Training
    training_task = model_training_op(
        dataset=extraction_task.outputs["dataset"]
    )
    
    # 3. Model Evaluation
    evaluation_task = model_evaluation_op(
        metrics=training_task.outputs["metrics"],
        threshold=accuracy_threshold
    )
    
    # 4. Conditional Deployment
    with dsl.Condition(
        evaluation_task.output == "true",
        name="deploy-decision"
    ):
        model_deployment_op(
            model=training_task.outputs["model"],
            project_id=project_id,
            region=region,
            serving_container_image_uri="us-docker.pkg.dev/vertex-ai/prediction/sklearn-cpu.1-0:latest"
        )

def compile_pipeline():
    """Compiles the pipeline into a JSON file."""
    compiler.Compiler().compile(
        pipeline_func=retraining_pipeline,
        package_path="sentinel_retraining_pipeline.json"
    )

if __name__ == "__main__":
    compile_pipeline()
