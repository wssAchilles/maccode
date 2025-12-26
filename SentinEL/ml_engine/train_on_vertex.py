"""
SentinEL Vertex AI 训练作业提交脚本
使用 Vertex AI CustomJob 在云端训练 LSTM 流失预测模型

功能:
    1. 创建 CustomJob 配置
    2. 提交训练作业到 Vertex AI
    3. 等待完成并记录 Artifact 位置
    4. 可选自动注册模型到 Model Registry

使用方法:
    python train_on_vertex.py \
        --project sentinel-ai-project-482208 \
        --region us-central1 \
        --data_path gs://sentinel-mlops-artifacts/training_data/sequences.csv \
        --staging_bucket gs://sentinel-mlops-artifacts

依赖:
    pip install google-cloud-aiplatform
"""

import argparse
import logging
import os
from datetime import datetime
from typing import Optional

from google.cloud import aiplatform
from google.cloud.aiplatform import CustomJob

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
DEFAULT_STAGING_BUCKET = "gs://sentinel-mlops-artifacts"

# 训练容器镜像 (PyTorch GPU)
TRAINING_IMAGE = "us-docker.pkg.dev/vertex-ai/training/pytorch-gpu.2-0.py310:latest"

# 机器配置
DEFAULT_MACHINE_TYPE = "n1-standard-4"
DEFAULT_ACCELERATOR_TYPE = "NVIDIA_TESLA_T4"
DEFAULT_ACCELERATOR_COUNT = 1


def submit_training_job(
    project_id: str,
    region: str,
    data_path: str,
    staging_bucket: str,
    job_name: Optional[str] = None,
    epochs: int = 20,
    batch_size: int = 64,
    learning_rate: float = 0.001,
    model_type: str = "lstm",
    machine_type: str = DEFAULT_MACHINE_TYPE,
    accelerator_type: Optional[str] = DEFAULT_ACCELERATOR_TYPE,
    accelerator_count: int = DEFAULT_ACCELERATOR_COUNT,
    use_gpu: bool = True,
    sync: bool = True
) -> str:
    """
    提交 Vertex AI 训练作业
    
    Args:
        project_id: GCP 项目 ID
        region: 区域 (如 us-central1)
        data_path: 训练数据 GCS 路径
        staging_bucket: 暂存 Bucket (不带 gs:// 前缀也可)
        job_name: 作业名称 (可选，默认自动生成)
        epochs: 训练轮数
        batch_size: 批次大小
        learning_rate: 学习率
        model_type: 模型类型
        machine_type: 机器类型
        accelerator_type: 加速器类型 (GPU)
        accelerator_count: 加速器数量
        use_gpu: 是否使用 GPU
        sync: 是否同步等待完成
        
    Returns:
        str: 模型 Artifact GCS 路径
    """
    # 初始化 Vertex AI
    aiplatform.init(
        project=project_id,
        location=region,
        staging_bucket=staging_bucket
    )
    
    # 生成作业名称
    if not job_name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        job_name = f"sentinel-churn-lstm-{timestamp}"
    
    logger.info(f"准备提交训练作业: {job_name}")
    logger.info(f"  项目: {project_id}")
    logger.info(f"  区域: {region}")
    logger.info(f"  数据路径: {data_path}")
    
    # 模型输出路径
    model_artifact_path = f"{staging_bucket}/models/{job_name}"
    
    # 训练参数
    training_args = [
        f"--data_path={data_path}",
        f"--epochs={epochs}",
        f"--batch_size={batch_size}",
        f"--learning_rate={learning_rate}",
        f"--model_type={model_type}",
        "--vocab_size=30",
        "--embed_dim=64",
        "--hidden_dim=128",
        "--seq_length=20"
    ]
    
    # 选择容器镜像
    container_image = TRAINING_IMAGE
    
    # 机器配置
    if use_gpu and accelerator_type:
        worker_pool_specs = [
            {
                "machine_spec": {
                    "machine_type": machine_type,
                    "accelerator_type": accelerator_type,
                    "accelerator_count": accelerator_count
                },
                "replica_count": 1,
                "container_spec": {
                    "image_uri": container_image,
                    "command": ["python", "-m", "ml_engine.training.train_script"],
                    "args": training_args
                }
            }
        ]
        logger.info(f"  机器类型: {machine_type} + {accelerator_count}x {accelerator_type}")
    else:
        # CPU 训练
        container_image = "us-docker.pkg.dev/vertex-ai/training/pytorch-cpu.2-0.py310:latest"
        worker_pool_specs = [
            {
                "machine_spec": {
                    "machine_type": machine_type
                },
                "replica_count": 1,
                "container_spec": {
                    "image_uri": container_image,
                    "command": ["python", "-m", "ml_engine.training.train_script"],
                    "args": training_args
                }
            }
        ]
        logger.info(f"  机器类型: {machine_type} (CPU)")
    
    # 创建 CustomJob
    custom_job = CustomJob(
        display_name=job_name,
        worker_pool_specs=worker_pool_specs,
        base_output_dir=model_artifact_path,
    )
    
    logger.info("提交训练作业...")
    
    # 提交作业
    custom_job.run(
        sync=sync,
        service_account=None,  # 使用默认服务账号
    )
    
    if sync:
        logger.info(f"训练作业完成!")
        logger.info(f"模型 Artifact 路径: {model_artifact_path}")
    else:
        logger.info(f"训练作业已提交 (异步模式)")
        logger.info(f"作业名称: {job_name}")
    
    return model_artifact_path


def submit_with_custom_container(
    project_id: str,
    region: str,
    data_path: str,
    staging_bucket: str,
    container_image: str,
    job_name: Optional[str] = None,
    **training_kwargs
) -> str:
    """
    使用自定义容器提交训练作业
    
    当需要自定义依赖或代码打包时使用此函数。
    
    Args:
        project_id: GCP 项目 ID
        region: 区域
        data_path: 训练数据路径
        staging_bucket: 暂存 Bucket
        container_image: 自定义容器镜像 (如 gcr.io/project/image:tag)
        job_name: 作业名称
        **training_kwargs: 训练参数
        
    Returns:
        str: 模型 Artifact 路径
    """
    aiplatform.init(
        project=project_id,
        location=region,
        staging_bucket=staging_bucket
    )
    
    if not job_name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        job_name = f"sentinel-churn-custom-{timestamp}"
    
    model_artifact_path = f"{staging_bucket}/models/{job_name}"
    
    # 构建训练参数
    training_args = [
        f"--data_path={data_path}",
        f"--epochs={training_kwargs.get('epochs', 20)}",
        f"--batch_size={training_kwargs.get('batch_size', 64)}",
    ]
    
    worker_pool_specs = [
        {
            "machine_spec": {
                "machine_type": training_kwargs.get("machine_type", "n1-standard-4")
            },
            "replica_count": 1,
            "container_spec": {
                "image_uri": container_image,
                "args": training_args
            }
        }
    ]
    
    custom_job = CustomJob(
        display_name=job_name,
        worker_pool_specs=worker_pool_specs,
        base_output_dir=model_artifact_path
    )
    
    logger.info(f"使用自定义容器提交作业: {container_image}")
    custom_job.run(sync=True)
    
    return model_artifact_path


def main():
    parser = argparse.ArgumentParser(description="SentinEL Vertex AI 训练作业提交")
    
    # GCP 配置
    parser.add_argument("--project", type=str, default=DEFAULT_PROJECT,
                        help="GCP 项目 ID")
    parser.add_argument("--region", type=str, default=DEFAULT_REGION,
                        help="Vertex AI 区域")
    parser.add_argument("--staging_bucket", type=str, default=DEFAULT_STAGING_BUCKET,
                        help="暂存 Bucket")
    
    # 数据配置
    parser.add_argument("--data_path", type=str, required=True,
                        help="训练数据 GCS 路径")
    
    # 作业配置
    parser.add_argument("--job_name", type=str, default=None,
                        help="作业名称 (可选)")
    parser.add_argument("--machine_type", type=str, default=DEFAULT_MACHINE_TYPE,
                        help="机器类型")
    parser.add_argument("--use_gpu", action="store_true", default=True,
                        help="使用 GPU")
    parser.add_argument("--no_gpu", action="store_true",
                        help="不使用 GPU (覆盖 --use_gpu)")
    parser.add_argument("--async_mode", action="store_true",
                        help="异步模式 (不等待完成)")
    
    # 训练参数
    parser.add_argument("--epochs", type=int, default=20,
                        help="训练轮数")
    parser.add_argument("--batch_size", type=int, default=64,
                        help="批次大小")
    parser.add_argument("--learning_rate", type=float, default=0.001,
                        help="学习率")
    parser.add_argument("--model_type", type=str, default="lstm",
                        choices=["lstm", "transformer"],
                        help="模型类型")
    
    args = parser.parse_args()
    
    use_gpu = args.use_gpu and not args.no_gpu
    
    # 提交作业
    model_path = submit_training_job(
        project_id=args.project,
        region=args.region,
        data_path=args.data_path,
        staging_bucket=args.staging_bucket,
        job_name=args.job_name,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        model_type=args.model_type,
        machine_type=args.machine_type,
        use_gpu=use_gpu,
        sync=not args.async_mode
    )
    
    print(f"\n模型 Artifact 路径: {model_path}")


if __name__ == "__main__":
    main()
