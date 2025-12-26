"""
SentinEL LSTM 训练脚本
在 Vertex AI Custom Job 容器内执行的训练逻辑

功能:
    1. 从 GCS 加载序列数据
    2. 创建 PyTorch DataLoader
    3. 训练 ChurnLSTM 模型
    4. 保存模型为 TorchScript 格式
    5. 上传 Artifacts 到 GCS

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
from pathlib import Path
from typing import Tuple

import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, random_split

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.churn_lstm import ChurnLSTM, create_model

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
) -> Tuple[float, float, float]:
    """
    评估模型
    
    Args:
        model: 模型
        dataloader: 验证数据加载器
        criterion: 损失函数
        device: 设备
        
    Returns:
        Tuple[float, float, float]: (平均损失, 准确率, AUC)
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
    
    # 计算 AUC
    try:
        from sklearn.metrics import roc_auc_score
        auc = roc_auc_score(all_labels, all_probs)
    except Exception:
        auc = 0.0
    
    return avg_loss, accuracy, auc


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
    model_type: str = "lstm"
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
    model = create_model(
        model_type=model_type,
        vocab_size=vocab_size,
        embed_dim=embed_dim,
        hidden_dim=hidden_dim
    ).to(device)
    
    logger.info(f"模型类型: {type(model).__name__}")
    logger.info(f"模型参数: {sum(p.numel() for p in model.parameters()):,}")
    
    # 损失函数和优化器
    criterion = nn.BCELoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=0.01)
    
    # 学习率调度器
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', factor=0.5, patience=3
    )
    
    # 训练循环
    best_auc = 0.0
    best_model_state = None
    
    for epoch in range(1, epochs + 1):
        # 训练
        train_loss = train_one_epoch(model, train_loader, criterion, optimizer, device)
        
        # 验证
        val_loss, val_acc, val_auc = evaluate(model, val_loader, criterion, device)
        
        # 更新学习率
        scheduler.step(val_loss)
        
        logger.info(
            f"Epoch {epoch}/{epochs} | "
            f"Train Loss: {train_loss:.4f} | "
            f"Val Loss: {val_loss:.4f} | "
            f"Val Acc: {val_acc:.4f} | "
            f"Val AUC: {val_auc:.4f}"
        )
        
        # 保存最佳模型
        if val_auc > best_auc:
            best_auc = val_auc
            best_model_state = model.state_dict().copy()
            logger.info(f"  ↳ 新最佳模型! AUC: {best_auc:.4f}")
    
    # 恢复最佳模型
    if best_model_state:
        model.load_state_dict(best_model_state)
    
    # 保存模型
    os.makedirs(model_dir, exist_ok=True)
    
    # 保存 PyTorch 权重
    weights_path = os.path.join(model_dir, "model_weights.pt")
    torch.save(model.state_dict(), weights_path)
    logger.info(f"模型权重已保存: {weights_path}")
    
    # 保存 TorchScript 格式（用于推理优化）
    model.eval()
    example_input = torch.randint(0, vocab_size, (1, seq_length)).to(device)
    traced_model = torch.jit.trace(model, example_input)
    
    torchscript_path = os.path.join(model_dir, "model.pt")
    traced_model.save(torchscript_path)
    logger.info(f"TorchScript 模型已保存: {torchscript_path}")
    
    # 保存模型配置
    config = {
        "model_type": model_type,
        "vocab_size": vocab_size,
        "embed_dim": embed_dim,
        "hidden_dim": hidden_dim,
        "seq_length": seq_length,
        "best_auc": best_auc
    }
    config_path = os.path.join(model_dir, "config.json")
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    logger.info(f"模型配置已保存: {config_path}")
    
    # 打印最终结果
    logger.info(f"\n{'='*50}")
    logger.info(f"训练完成 | 最佳 AUC: {best_auc:.4f}")
    logger.info(f"模型目录: {model_dir}")
    logger.info(f"{'='*50}")
    
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
    parser.add_argument("--seq_length", type=int, default=20,
                        help="序列长度")
    
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
        model_type=args.model_type
    )


if __name__ == "__main__":
    main()
