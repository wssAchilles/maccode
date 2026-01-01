"""
SentinEL 序列流失模型训练脚本（LSTM/Transformer）
在 Vertex AI Custom Job 容器内执行的训练逻辑

功能:
    1. 从 GCS 加载序列数据
    2. 创建 PyTorch DataLoader
    3. 训练 ChurnLSTM 或 Transformer 模型
    4. 保存 TorchScript + 配置 + 指标

使用方法 (本地测试):
    python train_script.py \
        --data_path ./training_data/sequences.csv \
        --model_dir ./output \
        --epochs 10

使用方法 (Vertex AI):
    由 train_on_vertex.py 自动提交

依赖:
    pip install torch pandas google-cloud-storage
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, random_split

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import ChurnLSTM, ChurnTransformer, create_model
try:
    from google.cloud import bigquery
    _HAS_BQ = True
except Exception:
    _HAS_BQ = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==============================================================================
# 数据集类
# ==============================================================================
class ChurnSequenceDataset(Dataset):
    """
    流失预测序列数据集
    
    从 CSV 文件加载数据，转换为 PyTorch Tensor。
    
    CSV 格式:
        user_id, event_sequence, label
        "123", "[2,3,4,5,...]", 0
        
    Attributes:
        sequences: Token ID 序列张量, 形状 (N, seq_length)
        labels: 标签张量, 形状 (N,)
    """
    
    def __init__(self, csv_path: str, seq_length: int = 20):
        """
        初始化数据集
        
        Args:
            csv_path: CSV 文件路径（支持 GCS gs:// 路径）
            seq_length: 期望的序列长度
        """
        logger.info(f"加载数据集: {csv_path}")
        
        # 读取 CSV
        df = pd.read_csv(csv_path)
        logger.info(f"数据量: {len(df)} 条")
        
        # 解析序列
        sequences = []
        labels = []
        
        for _, row in df.iterrows():
            # 解析 JSON 字符串为列表
            seq = json.loads(row['event_sequence'])
            
            # 确保序列长度一致
            if len(seq) > seq_length:
                seq = seq[-seq_length:]  # 截断
            elif len(seq) < seq_length:
                seq = [0] * (seq_length - len(seq)) + seq  # 填充
            
            sequences.append(seq)
            labels.append(int(row['label']))
        
        # 转换为 Tensor
        self.sequences = torch.tensor(sequences, dtype=torch.long)
        self.labels = torch.tensor(labels, dtype=torch.float32)
        
        # 统计
        churn_rate = self.labels.mean().item()
        logger.info(f"数据集统计 | 总数: {len(self.labels)}, 流失率: {churn_rate:.2%}")
    
    def __len__(self) -> int:
        return len(self.labels)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        获取单个样本
        
        Returns:
            Tuple[Tensor, Tensor]: (序列, 标签)
        """
        return self.sequences[idx], self.labels[idx]


# ==============================================================================
# 训练逻辑
# ==============================================================================
def train_one_epoch(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    optimizer: torch.optim.Optimizer,
    device: torch.device
) -> float:
    """
    训练一个 Epoch
    
    Args:
        model: 模型
        dataloader: 训练数据加载器
        criterion: 损失函数
        optimizer: 优化器
        device: 设备 (CPU/GPU)
        
    Returns:
        float: 平均损失
    """
    model.train()
    total_loss = 0.0
    
    for batch_idx, (sequences, labels) in enumerate(dataloader):
        sequences = sequences.to(device)
        labels = labels.to(device).unsqueeze(1)  # (batch,) -> (batch, 1)
        
        # 前向传播
        optimizer.zero_grad()
        outputs = model(sequences)
        loss = criterion(outputs, labels)
        
        # 反向传播
        loss.backward()
        
        # 梯度裁剪（防止梯度爆炸）
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        
        optimizer.step()
        
        total_loss += loss.item()
    
    avg_loss = total_loss / len(dataloader)
    return avg_loss


def evaluate(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    device: torch.device
) -> Tuple[float, float, float, float, float]:
    """
    评估模型
    
    Returns:
        Tuple: (avg_loss, accuracy, auc, pr_auc, logloss)
    """
    model.eval()
    total_loss = 0.0
    correct = 0
    total = 0
    all_probs = []
    all_labels = []
    
    with torch.no_grad():
        for sequences, labels in dataloader:
            sequences = sequences.to(device)
            labels = labels.to(device)
            
            outputs = model(sequences).squeeze(1)  # (batch, 1) -> (batch,)
            loss = criterion(outputs.unsqueeze(1), labels.unsqueeze(1))
            
            total_loss += loss.item()
            
            # 计算准确率
            preds = (outputs > 0.5).float()
            correct += (preds == labels).sum().item()
            total += labels.size(0)
            
            all_probs.extend(outputs.cpu().tolist())
            all_labels.extend(labels.cpu().tolist())
    
    avg_loss = total_loss / len(dataloader)
    accuracy = correct / total if total > 0 else 0.0
    
    # 计算 AUC/PR-AUC/Logloss（带安全兜底）
    try:
        from sklearn.metrics import roc_auc_score, average_precision_score, log_loss
        auc = roc_auc_score(all_labels, all_probs)
        pr_auc = average_precision_score(all_labels, all_probs)
        logloss = log_loss(all_labels, all_probs, labels=[0, 1])
    except Exception:
        auc, pr_auc, logloss = 0.0, 0.0, 0.0
    
    return avg_loss, accuracy, auc, pr_auc, logloss


def train(
    data_path: str,
    model_dir: str,
    epochs: int = 20,
    batch_size: int = 64,
    learning_rate: float = 0.001,
    vocab_size: int = 30,
    embed_dim: int = 64,
    hidden_dim: int = 128,
    seq_length: int = 20,
    model_type: str = "lstm",
    num_layers: int = 2,
    dropout: float = 0.3,
    num_heads: int = 4,
    ff_dim: int = 256,
    early_stop_patience: int = 5,
    weight_decay: float = 0.01,
) -> str:
    """
    完整训练流程
    
    Args:
        data_path: 训练数据 CSV 路径
        model_dir: 模型输出目录
        epochs: 训练轮数
        batch_size: 批次大小
        learning_rate: 学习率
        vocab_size: 词汇表大小
        embed_dim: Embedding 维度
        hidden_dim: LSTM 隐藏层维度
        seq_length: 序列长度
        model_type: 模型类型 ("lstm" 或 "transformer")
        num_layers: LSTM/Transformer 层数
        dropout: Dropout 概率
        num_heads: Transformer 头数
        ff_dim: Transformer FFN 维度
        early_stop_patience: 早停耐心轮数
        weight_decay: 权重衰减系数
        
    Returns:
        str: 保存的模型路径
    """
    # 设备选择
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"训练设备: {device}")
    
    # 加载数据集
    dataset = ChurnSequenceDataset(data_path, seq_length=seq_length)
    
    # 划分训练集和验证集 (80/20)
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = random_split(dataset, [train_size, val_size])
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    
    logger.info(f"训练集: {train_size}, 验证集: {val_size}")
    
    # 创建模型
    if model_type.lower() == "lstm":
        model_kwargs: Dict = {
            "embed_dim": embed_dim,
            "hidden_dim": hidden_dim,
            "num_layers": num_layers,
            "dropout": dropout,
        }
    else:
        model_kwargs = {
            "embed_dim": embed_dim,
            "num_heads": num_heads,
            "num_layers": num_layers,
            "ff_dim": ff_dim,
            "dropout": dropout,
            "max_seq_len": seq_length,
        }

    model = create_model(
        model_type=model_type,
        vocab_size=vocab_size,
        **model_kwargs,
    ).to(device)
    
    logger.info(f"模型类型: {type(model).__name__}")
    logger.info(f"模型参数: {sum(p.numel() for p in model.parameters()):,}")
    
    # 损失函数和优化器
    criterion = nn.BCELoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
    
    # 学习率调度器
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', factor=0.5, patience=3
    )
    
    # 训练循环
    best_metrics = {
        "epoch": 0,
        "val_auc": -1.0,
        "val_pr_auc": 0.0,
        "val_logloss": 0.0,
        "val_accuracy": 0.0,
        "train_loss": 0.0,
    }
    best_model_state = None
    no_improve_epochs = 0
    
    for epoch in range(1, epochs + 1):
        # 训练
        train_loss = train_one_epoch(model, train_loader, criterion, optimizer, device)
        
        # 验证
        val_loss, val_acc, val_auc, val_pr_auc, val_logloss = evaluate(model, val_loader, criterion, device)
        
        # 更新学习率
        scheduler.step(val_loss)
        
        logger.info(
            f"Epoch {epoch}/{epochs} | "
            f"Train Loss: {train_loss:.4f} | "
            f"Val Loss: {val_loss:.4f} | "
            f"Val Acc: {val_acc:.4f} | "
            f"Val AUC: {val_auc:.4f} | "
            f"Val PR-AUC: {val_pr_auc:.4f} | "
            f"Val LogLoss: {val_logloss:.4f}"
        )
        
        # 保存最佳模型
        if val_auc > best_metrics["val_auc"]:
            best_model_state = model.state_dict().copy()
            best_metrics.update(
                {
                    "epoch": epoch,
                    "val_auc": val_auc,
                    "val_pr_auc": val_pr_auc,
                    "val_logloss": val_logloss,
                    "val_accuracy": val_acc,
                    "train_loss": train_loss,
                }
            )
            no_improve_epochs = 0
            logger.info(f"  ↳ 新最佳模型! AUC: {val_auc:.4f}")
        else:
            no_improve_epochs += 1
            if no_improve_epochs >= early_stop_patience:
                logger.info(f"早停触发（{early_stop_patience} epochs 无提升），提前结束训练。")
                break
    
    # 恢复最佳模型
    if best_model_state:
        model.load_state_dict(best_model_state)
    
    # 保存模型与指标
    os.makedirs(model_dir, exist_ok=True)
    
    # 保存 PyTorch 权重
    weights_path = os.path.join(model_dir, "model_weights.pt")
    torch.save(model.state_dict(), weights_path)
    logger.info(f"模型权重已保存: {weights_path}")
    
    # 保存 TorchScript 格式（用于推理优化）
    model.eval()
    example_input = torch.randint(0, vocab_size, (1, seq_length)).to(device)
    torchscript_path = os.path.join(model_dir, "model.pt")
    try:
        traced_model = torch.jit.trace(model, example_input, strict=False)
        traced_model.save(torchscript_path)
        logger.info(f"TorchScript 模型已保存: {torchscript_path}")
    except Exception as e:
        logger.warning(f"TorchScript trace failed, fallback to script: {e}")
        scripted = torch.jit.script(model)
        scripted.save(torchscript_path)
        logger.info(f"TorchScript (script) 已保存: {torchscript_path}")
    
    # 推理延迟评估（单批）
    with torch.no_grad():
        start = time.time()
        _ = model(example_input)
        latency_ms = (time.time() - start) * 1000
    
    # 保存模型配置与指标
    config = {
        "model_type": model_type,
        "vocab_size": vocab_size,
        "embed_dim": embed_dim,
        "hidden_dim": hidden_dim,
        "seq_length": seq_length,
        "num_layers": num_layers,
        "num_heads": num_heads,
        "ff_dim": ff_dim,
        "dropout": dropout,
        "weight_decay": weight_decay,
        "early_stop_patience": early_stop_patience,
    }
    config_path = os.path.join(model_dir, "config.json")
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    logger.info(f"模型配置已保存: {config_path}")

    metrics = {
        "best_epoch": best_metrics["epoch"],
        "val_auc": best_metrics["val_auc"],
        "val_pr_auc": best_metrics["val_pr_auc"],
        "val_logloss": best_metrics["val_logloss"],
        "val_accuracy": best_metrics["val_accuracy"],
        "train_loss": best_metrics["train_loss"],
        "inference_latency_ms": latency_ms,
    }
    metrics_path = os.path.join(model_dir, "metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    logger.info(f"训练指标已保存: {metrics_path}")
    
    # 打印最终结果
    logger.info(f"\n{'='*50}")
    logger.info(
        f"训练完成 | 最佳 AUC: {best_metrics['val_auc']:.4f} | "
        f"最佳 PR-AUC: {best_metrics['val_pr_auc']:.4f} | "
        f"LogLoss: {best_metrics['val_logloss']:.4f} | "
        f"Latency(ms): {latency_ms:.2f}"
    )
    logger.info(f"模型目录: {model_dir}")
    logger.info(f"{'='*50}")

    # Vertex HPT 友好指标输出（AIP_METRIC_* 会被 Vertex 捕获）
    print(f"AIP_METRIC_val_auc={best_metrics['val_auc']}")
    print(f"AIP_METRIC_val_pr_auc={best_metrics['val_pr_auc']}")
    print(f"AIP_METRIC_val_logloss={best_metrics['val_logloss']}")
    print(f"AIP_METRIC_latency_ms={latency_ms}")

    # 可选：写入 BigQuery 训练指标表（通过 env BQ_TRAINING_METRICS_TABLE 启用）
    bq_table = os.environ.get("BQ_TRAINING_METRICS_TABLE")
    if bq_table and _HAS_BQ:
        try:
            client = bigquery.Client()
            row = {
                "job_time": time.time(),
                "model_type": model_type,
                "trial_id": os.environ.get("AIP_TRIAL_ID"),
                "hpt_job": os.environ.get("AIP_HP_TUNING_JOB_ID"),
                "val_auc": best_metrics["val_auc"],
                "val_pr_auc": best_metrics["val_pr_auc"],
                "val_logloss": best_metrics["val_logloss"],
                "val_accuracy": best_metrics["val_accuracy"],
                "train_loss": best_metrics["train_loss"],
                "latency_ms": latency_ms,
                "seq_length": seq_length,
                "num_layers": num_layers,
                "num_heads": num_heads,
                "ff_dim": ff_dim,
                "dropout": dropout,
                "learning_rate": learning_rate,
                "hidden_dim": hidden_dim,
            }
            errors = client.insert_rows_json(bq_table, [row])
            if errors:
                logger.warning(f"写入 BigQuery 训练指标失败: {errors}")
            else:
                logger.info(f"训练指标已写入 BigQuery: {bq_table}")
        except Exception as e:
            logger.warning(f"BigQuery 指标写入失败: {e}")
    
    return torchscript_path


def main():
    parser = argparse.ArgumentParser(description="SentinEL LSTM 训练脚本")
    
    # 数据参数
    parser.add_argument("--data_path", type=str, required=True,
                        help="训练数据 CSV 路径 (支持 GCS)")
    parser.add_argument("--model_dir", type=str, default="./output",
                        help="模型输出目录 (Vertex AI 使用 AIP_MODEL_DIR 环境变量)")
    
    # 训练参数
    parser.add_argument("--epochs", type=int, default=20,
                        help="训练轮数")
    parser.add_argument("--batch_size", type=int, default=64,
                        help="批次大小")
    parser.add_argument("--learning_rate", type=float, default=0.001,
                        help="学习率")
    
    # 模型参数
    parser.add_argument("--model_type", type=str, default="lstm",
                        choices=["lstm", "transformer"],
                        help="模型类型")
    parser.add_argument("--vocab_size", type=int, default=30,
                        help="词汇表大小")
    parser.add_argument("--embed_dim", type=int, default=64,
                        help="Embedding 维度")
    parser.add_argument("--hidden_dim", type=int, default=128,
                        help="LSTM 隐藏层维度")
    parser.add_argument("--num_layers", type=int, default=2,
                        help="LSTM/Transformer 层数")
    parser.add_argument("--dropout", type=float, default=0.3,
                        help="Dropout 概率")
    parser.add_argument("--num_heads", type=int, default=4,
                        help="Transformer 头数")
    parser.add_argument("--ff_dim", type=int, default=256,
                        help="Transformer FFN 维度")
    parser.add_argument("--seq_length", type=int, default=20,
                        help="序列长度")
    parser.add_argument("--early_stop_patience", type=int, default=5,
                        help="早停耐心轮数")
    parser.add_argument("--weight_decay", type=float, default=0.01,
                        help="权重衰减")
    
    args = parser.parse_args()
    
    # Vertex AI 使用 AIP_MODEL_DIR 环境变量
    model_dir = os.environ.get("AIP_MODEL_DIR", args.model_dir)
    
    # 开始训练
    train(
        data_path=args.data_path,
        model_dir=model_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        vocab_size=args.vocab_size,
        embed_dim=args.embed_dim,
        hidden_dim=args.hidden_dim,
        seq_length=args.seq_length,
        model_type=args.model_type,
        num_layers=args.num_layers,
        dropout=args.dropout,
        num_heads=args.num_heads,
        ff_dim=args.ff_dim,
        early_stop_patience=args.early_stop_patience,
        weight_decay=args.weight_decay,
    )


if __name__ == "__main__":
    main()
