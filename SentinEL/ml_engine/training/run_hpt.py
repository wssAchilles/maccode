"""
SentinEL Vertex AI Hyperparameter Tuning Job 提交脚本

功能:
    使用 Vertex AI Vizier (贝叶斯优化) 自动搜索最佳超参数组合

使用方法:
    1. 构建并推送训练镜像:
       cd ml_engine
       gcloud builds submit --tag gcr.io/sentinel-ai-project-482208/sentinel-train:latest .
    
    2. 提交 HPT 作业:
       python ml_engine/training/run_hpt.py \
           --project sentinel-ai-project-482208 \
           --region us-central1 \
           --data_gcs_path gs://sentinel-ai-project-482208-ml-data/training/train.csv \
           --val_gcs_path gs://sentinel-ai-project-482208-ml-data/training/val.csv \
           --max_trial_count 20 \
           --parallel_trial_count 4

依赖:
    pip install google-cloud-aiplatform
"""

import argparse
import logging
from datetime import datetime
from typing import Dict, List, Optional

from google.cloud import aiplatform
from google.cloud.aiplatform import hyperparameter_tuning as hpt

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# 默认配置
# =============================================================================
DEFAULT_PROJECT_ID = "sentinel-ai-project-482208"
DEFAULT_REGION = "us-central1"
DEFAULT_CONTAINER_URI = f"gcr.io/{DEFAULT_PROJECT_ID}/sentinel-train:latest"
DEFAULT_STAGING_BUCKET = f"gs://{DEFAULT_PROJECT_ID}-ml-staging"

# 机器配置
DEFAULT_MACHINE_TYPE = "n1-standard-4"
DEFAULT_ACCELERATOR_TYPE = "NVIDIA_TESLA_T4"
DEFAULT_ACCELERATOR_COUNT = 1

# HPT 配置
DEFAULT_MAX_TRIAL_COUNT = 20
DEFAULT_PARALLEL_TRIAL_COUNT = 4


# =============================================================================
# 参数空间定义
# =============================================================================
def get_parameter_spec() -> Dict[str, dict]:
    """
    定义超参数搜索空间
    
    使用 Vertex AI HPT SDK 格式定义参数规格
    
    Returns:
        Dict: 参数规格字典
    """
    return {
        # 学习率: 对数刻度搜索 [1e-4, 1e-2]
        "lr": hpt.DoubleParameterSpec(
            min=1e-4,
            max=1e-2,
            scale="log"
        ),
        
        # 批次大小: 离散值
        "batch_size": hpt.DiscreteParameterSpec(
            values=[32, 64, 128],
            scale="unit"
        ),
        
        # Transformer 嵌入维度
        # 注意: 选择能被常用 nhead 整除的值
        "d_model": hpt.DiscreteParameterSpec(
            values=[64, 128, 256],
            scale="unit"
        ),
        
        # 注意力头数
        # 代码中会验证 d_model % nhead == 0
        "nhead": hpt.DiscreteParameterSpec(
            values=[2, 4, 8],
            scale="unit"
        ),
        
        # Transformer 层数
        "num_layers": hpt.IntegerParameterSpec(
            min=1,
            max=4,
            scale="unit"
        ),
        
        # Dropout 比率
        "dropout": hpt.DoubleParameterSpec(
            min=0.1,
            max=0.5,
            scale="linear"
        ),
    }


def get_metric_spec() -> Dict[str, str]:
    """
    定义优化目标指标
    
    必须与 train_multimodal.py 中 aiplatform.log_metrics() 上报的 key 一致
    
    Returns:
        Dict: 指标规格 {metric_id: goal}
    """
    return {
        "val_auc": "maximize"  # 最大化验证集 AUC
    }


# =============================================================================
# HPT 作业创建
# =============================================================================
def create_hyperparameter_tuning_job(
    project_id: str,
    region: str,
    display_name: str,
    container_uri: str,
    data_gcs_path: str,
    val_gcs_path: Optional[str],
    output_gcs_path: str,
    staging_bucket: str,
    machine_type: str = DEFAULT_MACHINE_TYPE,
    accelerator_type: str = DEFAULT_ACCELERATOR_TYPE,
    accelerator_count: int = DEFAULT_ACCELERATOR_COUNT,
    max_trial_count: int = DEFAULT_MAX_TRIAL_COUNT,
    parallel_trial_count: int = DEFAULT_PARALLEL_TRIAL_COUNT,
    experiment_name: Optional[str] = None,
) -> aiplatform.HyperparameterTuningJob:
    """
    创建并提交 Vertex AI Hyperparameter Tuning Job
    
    Args:
        project_id: GCP 项目 ID
        region: 区域
        display_name: 作业显示名称
        container_uri: 训练容器镜像 URI
        data_gcs_path: 训练数据 GCS 路径
        val_gcs_path: 验证数据 GCS 路径 (可选)
        output_gcs_path: 输出模型 GCS 路径
        staging_bucket: 临时存储 bucket
        machine_type: 机器类型
        accelerator_type: GPU 类型
        accelerator_count: GPU 数量
        max_trial_count: 最大试验次数
        parallel_trial_count: 并行试验数
        experiment_name: Vertex AI Experiment 名称 (可选)
        
    Returns:
        HyperparameterTuningJob: 已提交的作业对象
    """
    # 初始化 Vertex AI
    aiplatform.init(
        project=project_id,
        location=region,
        staging_bucket=staging_bucket,
    )
    
    logger.info(f"初始化 Vertex AI | Project: {project_id} | Region: {region}")
    
    # 构造基础训练参数 (不包含超参数，由 Vizier 传入)
    base_args = [
        "--data_path", data_gcs_path,
        "--output_dir", output_gcs_path,
        "--epochs", "30",
        "--patience", "5",
        "--enable_vertex",
        "--project_id", project_id,
        "--location", region,
    ]
    
    if val_gcs_path:
        base_args.extend(["--val_data_path", val_gcs_path])
    
    if experiment_name:
        base_args.extend(["--experiment_name", experiment_name])
    
    # 定义 Worker Pool (单节点 GPU 训练)
    worker_pool_specs = [
        {
            "machine_spec": {
                "machine_type": machine_type,
                "accelerator_type": accelerator_type,
                "accelerator_count": accelerator_count,
            },
            "replica_count": 1,
            "container_spec": {
                "image_uri": container_uri,
                "args": base_args,
            },
        }
    ]
    
    # 创建 CustomJob 规格
    custom_job = aiplatform.CustomJob(
        display_name=f"{display_name}-worker",
        worker_pool_specs=worker_pool_specs,
    )
    
    # 获取参数空间和指标
    parameter_spec = get_parameter_spec()
    metric_spec = get_metric_spec()
    
    logger.info(f"参数空间: {list(parameter_spec.keys())}")
    logger.info(f"优化目标: {metric_spec}")
    logger.info(f"试验配置: max={max_trial_count}, parallel={parallel_trial_count}")
    
    # 创建 HyperparameterTuningJob
    hpt_job = aiplatform.HyperparameterTuningJob(
        display_name=display_name,
        custom_job=custom_job,
        metric_spec=metric_spec,
        parameter_spec=parameter_spec,
        max_trial_count=max_trial_count,
        parallel_trial_count=parallel_trial_count,
        # 搜索算法: 默认使用 ALGORITHM_UNSPECIFIED
        # Vertex AI 会自动选择最佳算法 (通常是贝叶斯优化)
    )
    
    logger.info(f"创建 HPT Job: {display_name}")
    
    # 提交作业 (非阻塞)
    # 注意: 使用 sync=False 时，作业会在后台创建
    # 需要等待一小段时间才能获取资源名称
    hpt_job.run(sync=False)
    
    # 等待作业资源创建完成
    import time
    max_wait = 30  # 最多等待 30 秒
    for i in range(max_wait):
        try:
            resource_name = hpt_job.resource_name
            if resource_name:
                break
        except RuntimeError:
            pass
        time.sleep(1)
        if i % 5 == 0:
            logger.info(f"等待作业创建中... ({i}s)")
    
    logger.info(f"✅ HPT Job 已提交!")
    logger.info(f"   作业名称: {display_name}")
    
    try:
        resource_name = hpt_job.resource_name
        job_id = resource_name.split('/')[-1]
        logger.info(f"   资源名称: {resource_name}")
        logger.info(f"   控制台 URL: https://console.cloud.google.com/vertex-ai/locations/{region}/training/{job_id}?project={project_id}")
    except Exception as e:
        logger.warning(f"   无法获取资源名称 (作业仍在创建中): {e}")
        logger.info(f"   请使用 'gcloud ai hp-tuning-jobs list --region={region}' 查看作业状态")
    
    return hpt_job


# =============================================================================
# 主函数
# =============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="提交 Vertex AI Hyperparameter Tuning Job",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 1. 首先构建并推送训练镜像
    cd ml_engine
    gcloud builds submit --tag gcr.io/sentinel-ai-project-482208/sentinel-train:latest .
    
    # 2. 提交 HPT 作业
    python ml_engine/training/run_hpt.py \\
        --project sentinel-ai-project-482208 \\
        --region us-central1 \\
        --data_gcs_path gs://sentinel-ai-project-482208-ml-data/training/train.csv \\
        --max_trial_count 20
        """
    )
    
    # 必需参数
    parser.add_argument(
        "--data_gcs_path", 
        type=str, 
        required=True,
        help="训练数据 GCS 路径 (如 gs://bucket/train.csv)"
    )
    
    # 可选参数
    parser.add_argument(
        "--val_gcs_path",
        type=str,
        default=None,
        help="验证数据 GCS 路径 (可选)"
    )
    parser.add_argument(
        "--project",
        type=str,
        default=DEFAULT_PROJECT_ID,
        help=f"GCP 项目 ID (默认: {DEFAULT_PROJECT_ID})"
    )
    parser.add_argument(
        "--region",
        type=str,
        default=DEFAULT_REGION,
        help=f"区域 (默认: {DEFAULT_REGION})"
    )
    parser.add_argument(
        "--container_uri",
        type=str,
        default=DEFAULT_CONTAINER_URI,
        help=f"训练容器镜像 URI (默认: {DEFAULT_CONTAINER_URI})"
    )
    parser.add_argument(
        "--staging_bucket",
        type=str,
        default=DEFAULT_STAGING_BUCKET,
        help=f"临时存储 bucket (默认: {DEFAULT_STAGING_BUCKET})"
    )
    parser.add_argument(
        "--output_gcs_path",
        type=str,
        default=None,
        help="模型输出 GCS 路径 (默认自动生成)"
    )
    parser.add_argument(
        "--job_name",
        type=str,
        default=None,
        help="作业名称 (默认自动生成)"
    )
    parser.add_argument(
        "--experiment_name",
        type=str,
        default="sentinel-churn-hpt",
        help="Vertex AI Experiment 名称"
    )
    
    # 机器配置
    parser.add_argument(
        "--machine_type",
        type=str,
        default=DEFAULT_MACHINE_TYPE,
        help=f"机器类型 (默认: {DEFAULT_MACHINE_TYPE})"
    )
    parser.add_argument(
        "--accelerator_type",
        type=str,
        default=DEFAULT_ACCELERATOR_TYPE,
        help=f"GPU 类型 (默认: {DEFAULT_ACCELERATOR_TYPE})"
    )
    parser.add_argument(
        "--accelerator_count",
        type=int,
        default=DEFAULT_ACCELERATOR_COUNT,
        help=f"GPU 数量 (默认: {DEFAULT_ACCELERATOR_COUNT})"
    )
    parser.add_argument(
        "--no_gpu",
        action="store_true",
        help="不使用 GPU (CPU only)"
    )
    
    # HPT 配置
    parser.add_argument(
        "--max_trial_count",
        type=int,
        default=DEFAULT_MAX_TRIAL_COUNT,
        help=f"最大试验次数 (默认: {DEFAULT_MAX_TRIAL_COUNT})"
    )
    parser.add_argument(
        "--parallel_trial_count",
        type=int,
        default=DEFAULT_PARALLEL_TRIAL_COUNT,
        help=f"并行试验数 (默认: {DEFAULT_PARALLEL_TRIAL_COUNT})"
    )
    
    args = parser.parse_args()
    
    # 生成默认值
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    
    if args.job_name is None:
        args.job_name = f"sentinel-hpt-{timestamp}"
    
    if args.output_gcs_path is None:
        args.output_gcs_path = f"{args.staging_bucket}/hpt-output/{args.job_name}"
    
    # 处理 no_gpu 选项
    accelerator_type = None if args.no_gpu else args.accelerator_type
    accelerator_count = 0 if args.no_gpu else args.accelerator_count
    
    logger.info("=" * 60)
    logger.info("SentinEL Hyperparameter Tuning Job")
    logger.info("=" * 60)
    logger.info(f"项目: {args.project}")
    logger.info(f"区域: {args.region}")
    logger.info(f"容器: {args.container_uri}")
    logger.info(f"训练数据: {args.data_gcs_path}")
    logger.info(f"验证数据: {args.val_gcs_path or '(自动分割)'}")
    logger.info(f"输出路径: {args.output_gcs_path}")
    logger.info(f"机器: {args.machine_type} + {accelerator_count}x {accelerator_type or 'CPU'}")
    logger.info(f"试验: {args.max_trial_count} total, {args.parallel_trial_count} parallel")
    logger.info("=" * 60)
    
    # 创建并提交 HPT 作业
    job = create_hyperparameter_tuning_job(
        project_id=args.project,
        region=args.region,
        display_name=args.job_name,
        container_uri=args.container_uri,
        data_gcs_path=args.data_gcs_path,
        val_gcs_path=args.val_gcs_path,
        output_gcs_path=args.output_gcs_path,
        staging_bucket=args.staging_bucket,
        machine_type=args.machine_type,
        accelerator_type=accelerator_type,
        accelerator_count=accelerator_count,
        max_trial_count=args.max_trial_count,
        parallel_trial_count=args.parallel_trial_count,
        experiment_name=args.experiment_name,
    )
    
    logger.info("")
    logger.info("📊 查看 Trial 结果:")
    logger.info(f"   gcloud ai hp-tuning-jobs list --region={args.region}")
    logger.info("")
    logger.info("🛑 取消作业:")
    logger.info(f"   gcloud ai hp-tuning-jobs cancel <JOB_ID> --region={args.region}")


if __name__ == "__main__":
    main()

