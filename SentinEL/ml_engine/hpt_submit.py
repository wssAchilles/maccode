"""
Vertex Hyperparameter Tuning 提交流水线

功能:
- 使用 Vertex HyperparameterTuningJob 对 churn 模型进行 HPT
- 搜索空间覆盖 lr/hidden_dim/num_layers/dropout/seq_length/ff_dim/num_heads
- 主优化指标: val_auc（在训练脚本中通过 AIP_METRIC_val_auc 输出）

前提:
- 训练脚本 ml_engine/training/train_script.py 已输出 AIP_METRIC_* 指标
- 可访问的 GCS data_path (CSV) 与 staging_bucket
- 需要 google-cloud-aiplatform>=1.38
"""

import argparse
import logging
from google.cloud import aiplatform

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def submit_hpt_job(
    project: str,
    region: str,
    staging_bucket: str,
    data_path: str,
    max_trial_count: int = 10,
    parallel_trial_count: int = 2,
    machine_type: str = "a2-highgpu-1g",
    accelerator_type: str | None = "NVIDIA_TESLA_A100",
    accelerator_count: int = 1,
    model_type: str = "transformer",
) -> str:
    """
    提交 Vertex HyperparameterTuningJob
    """
    aiplatform.init(project=project, location=region, staging_bucket=staging_bucket)

    # 训练容器镜像（与 train_on_vertex 对齐）
    worker_pool_specs = [
        {
            "machine_spec": {
                "machine_type": machine_type,
                **(
                    {
                        "accelerator_type": accelerator_type,
                        "accelerator_count": accelerator_count,
                    }
                    if accelerator_type
                    else {}
                ),
            },
            "replica_count": 1,
            "container_spec": {
                "image_uri": "us-docker.pkg.dev/vertex-ai/training/pytorch-gpu.2-1.py310:latest",
                "command": [
                    "python",
                    "-m",
                    "ml_engine.training.train_script",
                ],
                "args": [
                    f"--data_path={data_path}",
                    "--model_dir=$(AIP_MODEL_DIR)",
                    f"--model_type={model_type}",
                    # Hyperparameters will be injected by HPT as {{parameter_id}}
                    "--learning_rate={{learning_rate}}",
                    "--hidden_dim={{hidden_dim}}",
                    "--num_layers={{num_layers}}",
                    "--dropout={{dropout}}",
                    "--seq_length={{seq_length}}",
                    "--num_heads={{num_heads}}",
                    "--ff_dim={{ff_dim}}",
                ],
            },
        }
    ]

    parameter_spec = {
        "learning_rate": aiplatform.hyperparameter_tuning.DoubleParameterSpec(
            min=1e-4, max=1e-2, scale="log"
        ),
        "hidden_dim": aiplatform.hyperparameter_tuning.DiscreteParameterSpec(
            values=[64, 128, 256], scale=None
        ),
        "num_layers": aiplatform.hyperparameter_tuning.IntegerParameterSpec(
            min=1, max=4, scale=None
        ),
        "dropout": aiplatform.hyperparameter_tuning.DoubleParameterSpec(
            min=0.0, max=0.5, scale="linear"
        ),
        "seq_length": aiplatform.hyperparameter_tuning.DiscreteParameterSpec(
            values=[20, 30, 40], scale=None
        ),
        "num_heads": aiplatform.hyperparameter_tuning.DiscreteParameterSpec(
            values=[2, 4, 8], scale=None
        ),
        "ff_dim": aiplatform.hyperparameter_tuning.DiscreteParameterSpec(
            values=[128, 256, 512], scale=None
        ),
    }

    # 主指标最大化 val_auc
    metric_spec = {"val_auc": "maximize"}

    hpt_job = aiplatform.HyperparameterTuningJob(
        display_name="sentinel-churn-hpt",
        custom_job=aiplatform.CustomJob(
            display_name="sentinel-churn-hpt-trial",
            worker_pool_specs=worker_pool_specs,
        ),
        metric_spec=metric_spec,
        parameter_spec=parameter_spec,
        max_trial_count=max_trial_count,
        parallel_trial_count=parallel_trial_count,
    )

    print("Submitting HyperparameterTuningJob (SYNC)...")
    try:
        hpt_job.run(sync=True)
        print("Job run called successfully.")
    except Exception as e:
        print(f"Error calling hpt_job.run: {e}")
        # Iterate over details if available
        if hasattr(e, 'message'):
            print(e.message)
        raise
    logger.info(f"HPT job submitted: {hpt_job.resource_name}")
    return hpt_job.resource_name


def main():
    parser = argparse.ArgumentParser(description="Submit Vertex HPT for churn model")
    parser.add_argument("--project", type=str, required=True)
    parser.add_argument("--region", type=str, default="us-central1")
    parser.add_argument("--staging_bucket", type=str, default="gs://sentinel-mlops-artifacts-sentinel-ai-project-482208", help="gs://bucket")
    parser.add_argument("--data_path", type=str, default="gs://sentinel-mlops-artifacts-sentinel-ai-project-482208/training_data/sequences.csv", help="gs:// path to sequences.csv")
    parser.add_argument("--max_trials", type=int, default=10)
    parser.add_argument("--parallel_trials", type=int, default=2)
    parser.add_argument("--machine_type", type=str, default="a2-highgpu-1g")
    parser.add_argument("--accelerator_type", type=str, default="NVIDIA_TESLA_A100")
    parser.add_argument("--accelerator_count", type=int, default=1)
    parser.add_argument("--model_type", type=str, default="transformer", choices=["transformer", "lstm"])

    args = parser.parse_args()

    job_name = submit_hpt_job(
        project=args.project,
        region=args.region,
        staging_bucket=args.staging_bucket,
        data_path=args.data_path,
        max_trial_count=args.max_trials,
        parallel_trial_count=args.parallel_trials,
        machine_type=args.machine_type,
        accelerator_type=args.accelerator_type,
        accelerator_count=args.accelerator_count,
        model_type=args.model_type,
    )
    print(f"HPT Job submitted: {job_name}")


if __name__ == "__main__":
    main()
