"""
SentinEL 模型部署脚本
将训练好的 LSTM 模型部署到 Vertex AI Endpoint 进行在线预测

功能:
    1. 注册模型到 Vertex AI Model Registry
    2. 创建 Endpoint (如果不存在)
    3. 部署模型到 Endpoint
    4. 测试推理端点

使用方法:
    python deploy_endpoint.py \
        --project sentinel-ai-project-482208 \
        --region us-central1 \
        --model_artifact_path gs://sentinel-mlops-artifacts/models/sentinel-churn-lstm-xxx

依赖:
    pip install google-cloud-aiplatform
"""

import argparse
import logging
import os
from typing import Optional, Dict, List, Any

from google.cloud import aiplatform
from google.cloud.aiplatform import Model, Endpoint

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==============================================================================
# 默认配置
# ==============================================================================
DEFAULT_PROJECT = "sentinel-ai-project-482208"
DEFAULT_REGION = "us-central1"

# 推理容器镜像 (PyTorch)
# 使用预构建的 PyTorch 推理容器
SERVING_CONTAINER_IMAGE = "us-docker.pkg.dev/vertex-ai/prediction/pytorch-cpu.2-0:latest"

# Endpoint 配置
DEFAULT_MACHINE_TYPE = "n1-standard-4"
DEFAULT_MIN_REPLICAS = 1
DEFAULT_MAX_REPLICAS = 2


def register_model(
    project_id: str,
    region: str,
    model_artifact_path: str,
    model_display_name: str,
    serving_container_image: str = SERVING_CONTAINER_IMAGE,
    description: str = "SentinEL LSTM 流失预测模型"
) -> Model:
    """
    注册模型到 Vertex AI Model Registry
    
    Args:
        project_id: GCP 项目 ID
        region: 区域
        model_artifact_path: 模型 Artifact GCS 路径
        model_display_name: 模型显示名称
        serving_container_image: 推理容器镜像
        description: 模型描述
        
    Returns:
        Model: 注册的模型对象
    """
    logger.info(f"注册模型: {model_display_name}")
    logger.info(f"  Artifact 路径: {model_artifact_path}")
    
    aiplatform.init(project=project_id, location=region)
    
    # 注册模型
    model = Model.upload(
        display_name=model_display_name,
        artifact_uri=model_artifact_path,
        serving_container_image_uri=serving_container_image,
        description=description,
        labels={
            "project": "sentinel",
            "model_type": "churn_lstm",
            "framework": "pytorch"
        }
    )
    
    logger.info(f"模型注册成功!")
    logger.info(f"  Model Resource Name: {model.resource_name}")
    
    return model


def create_endpoint(
    project_id: str,
    region: str,
    endpoint_display_name: str = "sentinel-churn-endpoint",
    description: str = "SentinEL 流失预测在线端点"
) -> Endpoint:
    """
    创建 Vertex AI Endpoint
    
    Args:
        project_id: GCP 项目 ID
        region: 区域
        endpoint_display_name: Endpoint 显示名称
        description: Endpoint 描述
        
    Returns:
        Endpoint: 创建的 Endpoint 对象
    """
    aiplatform.init(project=project_id, location=region)
    
    # 检查是否已存在同名 Endpoint
    endpoints = Endpoint.list(
        filter=f'display_name="{endpoint_display_name}"'
    )
    
    if endpoints:
        logger.info(f"Endpoint 已存在: {endpoint_display_name}")
        return endpoints[0]
    
    # 创建新 Endpoint
    logger.info(f"创建 Endpoint: {endpoint_display_name}")
    
    endpoint = Endpoint.create(
        display_name=endpoint_display_name,
        description=description,
        labels={
            "project": "sentinel",
            "service": "churn_prediction"
        }
    )
    
    logger.info(f"Endpoint 创建成功!")
    logger.info(f"  Endpoint Resource Name: {endpoint.resource_name}")
    
    return endpoint


def deploy_model_to_endpoint(
    model: Model,
    endpoint: Endpoint,
    machine_type: str = DEFAULT_MACHINE_TYPE,
    min_replica_count: int = DEFAULT_MIN_REPLICAS,
    max_replica_count: int = DEFAULT_MAX_REPLICAS,
    traffic_percentage: int = 100
) -> None:
    """
    将模型部署到 Endpoint
    
    Args:
        model: 注册的模型
        endpoint: 目标 Endpoint
        machine_type: 机器类型
        min_replica_count: 最小副本数
        max_replica_count: 最大副本数
        traffic_percentage: 流量百分比
    """
    logger.info(f"部署模型到 Endpoint...")
    logger.info(f"  模型: {model.display_name}")
    logger.info(f"  Endpoint: {endpoint.display_name}")
    logger.info(f"  机器类型: {machine_type}")
    logger.info(f"  副本范围: {min_replica_count} - {max_replica_count}")
    
    # 部署模型
    model.deploy(
        endpoint=endpoint,
        machine_type=machine_type,
        min_replica_count=min_replica_count,
        max_replica_count=max_replica_count,
        traffic_percentage=traffic_percentage,
        sync=True  # 同步等待部署完成
    )
    
    logger.info(f"部署完成!")


def test_endpoint(
    endpoint: Endpoint,
    test_sequence: List[int]
) -> Dict[str, Any]:
    """
    测试 Endpoint 推理
    
    Args:
        endpoint: Endpoint 对象
        test_sequence: 测试事件序列 (Token IDs)
        
    Returns:
        Dict: 预测结果
    """
    logger.info(f"测试 Endpoint 推理...")
    
    # 构造请求
    instances = [
        {"sequence": test_sequence}
    ]
    
    # 调用预测
    prediction = endpoint.predict(instances)
    
    logger.info(f"预测结果: {prediction.predictions}")
    
    return {
        "predictions": prediction.predictions,
        "deployed_model_id": prediction.deployed_model_id
    }


def deploy_pipeline(
    project_id: str,
    region: str,
    model_artifact_path: str,
    model_display_name: str = "sentinel-churn-lstm",
    endpoint_display_name: str = "sentinel-churn-endpoint",
    machine_type: str = DEFAULT_MACHINE_TYPE,
    run_test: bool = True
) -> Dict[str, str]:
    """
    完整部署流程
    
    Args:
        project_id: GCP 项目 ID
        region: 区域
        model_artifact_path: 模型 Artifact 路径
        model_display_name: 模型名称
        endpoint_display_name: Endpoint 名称
        machine_type: 机器类型
        run_test: 是否运行测试
        
    Returns:
        Dict: 包含 model_name 和 endpoint_name
    """
    logger.info("=" * 60)
    logger.info("SentinEL 模型部署流程")
    logger.info("=" * 60)
    
    # 1. 注册模型
    model = register_model(
        project_id=project_id,
        region=region,
        model_artifact_path=model_artifact_path,
        model_display_name=model_display_name
    )
    
    # 2. 创建/获取 Endpoint
    endpoint = create_endpoint(
        project_id=project_id,
        region=region,
        endpoint_display_name=endpoint_display_name
    )
    
    # 3. 部署模型
    deploy_model_to_endpoint(
        model=model,
        endpoint=endpoint,
        machine_type=machine_type
    )
    
    # 4. 测试 (可选)
    if run_test:
        # 使用示例序列测试 (PAD + 一些事件)
        test_sequence = [0, 0, 0, 0, 0, 2, 3, 4, 11, 12, 14, 5, 3, 2, 2, 3, 4, 5, 6, 8]
        try:
            result = test_endpoint(endpoint, test_sequence)
            logger.info(f"测试预测结果: {result}")
        except Exception as e:
            logger.warning(f"测试失败 (可能是容器格式问题): {e}")
    
    # 5. 打印部署信息
    logger.info("\n" + "=" * 60)
    logger.info("部署完成!")
    logger.info("=" * 60)
    logger.info(f"模型 Resource Name: {model.resource_name}")
    logger.info(f"Endpoint Resource Name: {endpoint.resource_name}")
    logger.info(f"Endpoint ID: {endpoint.name}")
    
    return {
        "model_resource_name": model.resource_name,
        "endpoint_resource_name": endpoint.resource_name,
        "endpoint_id": endpoint.name
    }


def get_endpoint_by_name(
    project_id: str,
    region: str,
    endpoint_display_name: str
) -> Optional[Endpoint]:
    """
    根据名称获取 Endpoint
    
    Args:
        project_id: 项目 ID
        region: 区域
        endpoint_display_name: Endpoint 显示名称
        
    Returns:
        Optional[Endpoint]: Endpoint 对象或 None
    """
    aiplatform.init(project=project_id, location=region)
    
    endpoints = Endpoint.list(
        filter=f'display_name="{endpoint_display_name}"'
    )
    
    return endpoints[0] if endpoints else None


def main():
    parser = argparse.ArgumentParser(description="SentinEL 模型部署脚本")
    
    # GCP 配置
    parser.add_argument("--project", type=str, default=DEFAULT_PROJECT,
                        help="GCP 项目 ID")
    parser.add_argument("--region", type=str, default=DEFAULT_REGION,
                        help="Vertex AI 区域")
    
    # 模型配置
    parser.add_argument("--model_artifact_path", type=str, required=True,
                        help="模型 Artifact GCS 路径")
    parser.add_argument("--model_name", type=str, default="sentinel-churn-lstm",
                        help="模型显示名称")
    parser.add_argument("--endpoint_name", type=str, default="sentinel-churn-endpoint",
                        help="Endpoint 显示名称")
    
    # 部署配置
    parser.add_argument("--machine_type", type=str, default=DEFAULT_MACHINE_TYPE,
                        help="机器类型")
    parser.add_argument("--skip_test", action="store_true",
                        help="跳过部署后测试")
    
    args = parser.parse_args()
    
    # 执行部署
    result = deploy_pipeline(
        project_id=args.project,
        region=args.region,
        model_artifact_path=args.model_artifact_path,
        model_display_name=args.model_name,
        endpoint_display_name=args.endpoint_name,
        machine_type=args.machine_type,
        run_test=not args.skip_test
    )
    
    print("\n部署结果:")
    for key, value in result.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
