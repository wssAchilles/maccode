import subprocess
import sys
import os
import random
import json
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_trial(trial_id, params, data_path, val_data_path, base_output_dir):
    logger.info(f"Start Trial {trial_id}...")
    
    trial_output_dir = os.path.join(base_output_dir, f"trial_{trial_id}")
    os.makedirs(trial_output_dir, exist_ok=True)
    
    # 构建命令
    # 注意: 不添加 --enable_vertex 标志，确保纯本地运行
    cmd = [
        sys.executable, "ml_engine/training/train_multimodal.py",
        "--data_path", data_path,
        "--val_data_path", val_data_path,
        "--output_dir", trial_output_dir,
        "--epochs", "15",            # 适量 Epoch
        "--patience", "5",           # Early Stopping
    ]
    
    # 添加超参数
    for k, v in params.items():
        cmd.extend([f"--{k}", str(v)])
    
    
    # 启用 MPS Fallback
    env = os.environ.copy()
    env["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
    
    # 运行训练
    try:
        # capture_output=True 可以隐藏子进程的冗长日志，如果想看实时日志可以去掉
        # 这里我们选择打印简要信息，遇到错误再打印完整日志
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)
        
        # 检查结果
        config_path = os.path.join(trial_output_dir, "model_config.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
                best_auc = config.get("best_auc", 0.0)
                logger.info(f"Trial {trial_id} Finished | AUC: {best_auc:.4f}")
                return best_auc, trial_output_dir
        else:
            logger.error(f"Trial {trial_id} Failed: output config not found.")
            # 打印部分日志以便调试
            logger.error(f"Tail of stdout:\n{result.stdout[-500:]}")
            return 0.0, trial_output_dir
            
    except subprocess.CalledProcessError as e:
        logger.error(f"Trial {trial_id} Crashed:\n{e.stderr}")
        return 0.0, trial_output_dir

def main():
    # 参数空间
    param_grid = {
        "lr": [1e-4, 5e-4, 1e-3, 2e-3],
        "batch_size": [32, 64],
        "d_model": [32, 64, 128],
        "num_layers": [1, 2, 4],
        "dropout": [0.1, 0.3, 0.5]
    }
    
    # 路径 (根据 find_by_name 的结果调整)
    DATA_PATH = "ml_engine/data/train.csv"
    VAL_PATH = "ml_engine/data/val.csv"
    
    # 确保数据存在
    if not os.path.exists(DATA_PATH) or not os.path.exists(VAL_PATH):
        logger.error(f"Data not found! Please check {DATA_PATH} and {VAL_PATH}")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    BASE_OUTPUT_DIR = os.path.abspath(f"ml_engine/local_hpt_output/{timestamp}")
    
    logger.info(f"Starting Local HPT on Mac (MPS/CPU) | Output: {BASE_OUTPUT_DIR}")
    
    num_trials = 5  # 演示用 5 次，实际可更多
    best_overall_auc = 0.0
    best_trial_path = None
    best_params = None
    
    results = []
    
    for i in range(num_trials):
        # 随机采样参数
        current_params = {
            k: random.choice(v) for k, v in param_grid.items()
        }
        # 约束: nhead 必须能整除 d_model
        d_model = current_params["d_model"]
        if d_model % 4 == 0:
             current_params["nhead"] = 4
        elif d_model % 2 == 0:
             current_params["nhead"] = 2
        else:
             current_params["nhead"] = 1
             
        logger.info(f"------------------------------------------------------------")
        logger.info(f"Trial {i+1}/{num_trials} Params: {current_params}")
        
        auc, path = run_trial(i+1, current_params, DATA_PATH, VAL_PATH, BASE_OUTPUT_DIR)
        
        results.append({
            "trial": i+1,
            "params": current_params,
            "auc": auc,
            "path": path
        })
        
        if auc > best_overall_auc:
            best_overall_auc = auc
            best_trial_path = path
            best_params = current_params
    
    # 总结
    logger.info("="*60)
    logger.info("HPT Summary:")
    for r in results:
        logger.info(f"  Trial {r['trial']}: AUC={r['auc']:.4f} | {r['params']}")
    
    logger.info("-" * 60)
    logger.info(f"Best Trial AUC: {best_overall_auc:.4f}")
    logger.info(f"Best Params: {best_params}")
    logger.info(f"Best Model Path: {best_trial_path}")
    logger.info("="*60)
    
    # 保存最佳信息以便后续步骤读取
    summary_path = os.path.join(BASE_OUTPUT_DIR, "hpt_summary.json")
    with open(summary_path, "w") as f:
        json.dump({
            "best_auc": best_overall_auc,
            "best_params": best_params,
            "best_model_path": best_trial_path,
            "trials": results
        }, f, indent=2)
    logger.info(f"Summary saved to {summary_path}")

if __name__ == "__main__":
    main()
