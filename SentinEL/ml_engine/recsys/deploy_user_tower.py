"""
SentinEL User Tower 部署脚本

将训练好的 User Tower SavedModel 部署到 Vertex AI Prediction Endpoint
"""

import argparse
import logging
from google.cloud import aiplatform

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_PROJECT = "sentinel-ai-project-482208"
DEFAULT_REGION = "us-central1"
DEFAULT_BUCKET = "sentinel-mlops-artifacts-sentinel-ai-project-482208"
MODEL_ARTIFACT_URI = f"gs://{DEFAULT_BUCKET}/recsys/models/saved_user_model"

def deploy_user_tower(
    project_id: str,
    region: str,
    model_artifact_uri: str,
    model_display_name: str = "sentinel-user-tower",
    endpoint_display_name: str = "sentinel-user-tower-endpoint",
    machine_type: str = "n1-standard-2"
):
    """
    部署 User Tower 模型到 Vertex AI
    
    Args:
        project_id: GCP 项目 ID
        region: 区域
        model_artifact_uri: GCS 上的 SavedModel 路径
        model_display_name: 模型显示名称
        endpoint_display_name: Endpoint 显示名称
        machine_type: 机器类型
    """
    # 初始化
    aiplatform.init(project=project_id, location=region)
    
    # 1. 检查/上传模型
    logger.info(f"Checking for existing model: {model_display_name}")
    models = aiplatform.Model.list(filter=f'display_name="{model_display_name}"')
    
    if models:
        model = models[0]
        logger.info(f"Model already exists: {model.resource_name}")
    else:
        logger.info(f"Uploading model from {model_artifact_uri}")
        model = aiplatform.Model.upload(
            display_name=model_display_name,
            artifact_uri=model_artifact_uri,
            serving_container_image_uri="us-docker.pkg.dev/vertex-ai/prediction/tf2-cpu.2-15:latest",
            description="SentinEL User Tower for recommendation system",
            sync=True
        )
        logger.info(f"Model uploaded: {model.resource_name}")
    
    # 2. 检查/创建 Endpoint
    logger.info(f"Checking for existing endpoint: {endpoint_display_name}")
    endpoints = aiplatform.Endpoint.list(filter=f'display_name="{endpoint_display_name}"')
    
    if endpoints:
        endpoint = endpoints[0]
        logger.info(f"Endpoint already exists: {endpoint.resource_name}")
    else:
        logger.info(f"Creating endpoint: {endpoint_display_name}")
        endpoint = aiplatform.Endpoint.create(
            display_name=endpoint_display_name,
            description="Endpoint for SentinEL User Tower predictions",
            sync=True
        )
        logger.info(f"Endpoint created: {endpoint.resource_name}")
    
    # 3. 部署模型到 Endpoint (如果尚未部署)
    deployed_models = endpoint.list_models()
    already_deployed = any(dm.model == model.resource_name for dm in deployed_models)
    
    if already_deployed:
        logger.info("Model already deployed to endpoint")
    else:
        logger.info(f"Deploying model to endpoint...")
        model.deploy(
            endpoint=endpoint,
            deployed_model_display_name="user-tower-v1",
            machine_type="e2-standard-2",  # 最小机器类型 (2 vCPU)
            min_replica_count=1,
            max_replica_count=1,  # 固定 1 副本以节省配额
            traffic_percentage=100,
            sync=True
        )
        logger.info("Model deployment complete!")
    
    # 4. 输出结果
    logger.info("\n" + "=" * 50)
    logger.info("USER TOWER DEPLOYMENT SUCCESSFUL")
    logger.info("=" * 50)
    logger.info(f"Model Resource Name: {model.resource_name}")
    logger.info(f"Endpoint Resource Name: {endpoint.resource_name}")
    logger.info(f"Endpoint ID: {endpoint.name}")
    logger.info("=" * 50)
    
    return {
        "model_resource_name": model.resource_name,
        "endpoint_resource_name": endpoint.resource_name,
        "endpoint_id": endpoint.name
    }


def main():
    parser = argparse.ArgumentParser(description="Deploy User Tower to Vertex AI")
    parser.add_argument("--project", type=str, default=DEFAULT_PROJECT)
    parser.add_argument("--region", type=str, default=DEFAULT_REGION)
    parser.add_argument("--model_uri", type=str, default=MODEL_ARTIFACT_URI)
    
    args = parser.parse_args()
    
    deploy_user_tower(
        project_id=args.project,
        region=args.region,
        model_artifact_uri=args.model_uri
    )


if __name__ == "__main__":
    main()
