"""
SentinEL 多模态 Transformer 训练脚本
生产级训练流程，集成 Vertex AI Experiments

功能:
    1. 加载多模态数据 (事件序列 + 类别特征 + 数值特征)
    2. 训练 MultimodalChurnTransformer 模型
    3. 实时上报指标到 Vertex AI Experiments
    4. 支持 Early Stopping 和模型检查点
    5. 保存模型权重和配置 (用于推理服务)

运行方式:
    python ml_engine/training/train_multimodal.py \
        --data_path ./data/train.csv \
        --val_data_path ./data/val.csv \
        --epochs 50 \
        --batch_size 64 \
        --lr 0.001 \
        --d_model 64 \
        --nhead 4 \
        --num_layers 2 \
        --dropout 0.1 \
        --output_dir ./output

依赖:
    pip install torch pandas scikit-learn google-cloud-aiplatform
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import roc_auc_score

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ml_engine.models.churn_transformer import MultimodalChurnTransformer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# =============================================================================
# 事件词汇表 (与 prediction_service.py 保持一致)
# =============================================================================
EVENT_VOCAB: Dict[str, int] = {
    "<PAD>": 0,
    "<UNK>": 1,
    "page_view": 2,
    "view_item": 3,
    "add_to_cart": 4,
    "remove_from_cart": 5,
    "begin_checkout": 6,
    "add_payment_info": 7,
    "purchase": 8,
    "view_promotion": 9,
    "select_promotion": 10,
    "check_policy": 11,
    "view_returns": 12,
    "contact_support": 13,
    "rage_click": 14,
    "session_start": 15,
    "session_end": 16,
    "scroll_to_bottom": 17,
    "form_abandon": 18,
    "coupon_apply": 19,
    "coupon_fail": 20,
    "wishlist_add": 21,
    "wishlist_remove": 22,
    "search": 23,
    "filter_apply": 24,
    "compare_items": 25,
    "share_item": 26,
    "review_read": 27,
    "review_write": 28,
}


# =============================================================================
# 多模态数据集
# =============================================================================
class MultimodalChurnDataset(Dataset):
    """
    多模态流失预测数据集
    
    支持三种输入:
        1. event_sequence: 事件 ID 序列
        2. categorical_features: 类别特征 (已编码为索引)
        3. numerical_features: 数值特征 (已归一化)
    """
    
    def __init__(
        self,
        df: pd.DataFrame,
        event_col: str = 'event_sequence',
        cat_cols: List[str] = None,
        num_cols: List[str] = None,
        label_col: str = 'churned',
        max_seq_len: int = 20,
        cat_encoders: Dict[str, LabelEncoder] = None,
        num_scaler: StandardScaler = None,
        fit_transforms: bool = False,
    ):
        """
        Args:
            df: 输入 DataFrame
            event_col: 事件序列列名 (字符串或列表)
            cat_cols: 类别特征列名列表
            num_cols: 数值特征列名列表
            label_col: 标签列名
            max_seq_len: 最大序列长度
            cat_encoders: 类别编码器字典 (外部传入或内部拟合)
            num_scaler: 数值归一化器 (外部传入或内部拟合)
            fit_transforms: 是否在此数据集上拟合转换器
        """
        self.df = df.reset_index(drop=True)
        self.event_col = event_col
        self.cat_cols = cat_cols or []
        self.num_cols = num_cols or []
        self.label_col = label_col
        self.max_seq_len = max_seq_len
        
        # 初始化或使用外部编码器
        self.cat_encoders = cat_encoders or {}
        self.num_scaler = num_scaler
        
        # 拟合转换器
        if fit_transforms:
            self._fit_transforms()
        
        # 预处理数据
        self._preprocess()
        
        logger.info(f"数据集初始化完成 | 样本数: {len(self.df)}")
    
    def _fit_transforms(self):
        """拟合类别编码器和数值归一化器"""
        # 类别编码
        for col in self.cat_cols:
            if col not in self.cat_encoders:
                encoder = LabelEncoder()
                self.df[col] = self.df[col].fillna('__UNKNOWN__')
                encoder.fit(self.df[col])
                self.cat_encoders[col] = encoder
        
        # 数值归一化
        if self.num_cols and self.num_scaler is None:
            self.num_scaler = StandardScaler()
            num_data = self.df[self.num_cols].fillna(0).values
            self.num_scaler.fit(num_data)
    
    def _preprocess(self):
        """预处理所有数据"""
        # 处理事件序列
        self.event_sequences = []
        for idx, row in self.df.iterrows():
            seq = row[self.event_col]
            token_ids = self._tokenize_events(seq)
            self.event_sequences.append(token_ids)
        
        # 处理类别特征
        self.cat_features = []
        for idx, row in self.df.iterrows():
            cat_indices = []
            for col in self.cat_cols:
                val = row[col] if pd.notna(row[col]) else '__UNKNOWN__'
                encoder = self.cat_encoders.get(col)
                if encoder:
                    try:
                        idx_val = encoder.transform([val])[0]
                    except ValueError:
                        idx_val = 0  # 未知类别
                else:
                    idx_val = 0
                cat_indices.append(idx_val)
            self.cat_features.append(cat_indices)
        
        # 处理数值特征
        if self.num_cols:
            num_data = self.df[self.num_cols].fillna(0).values
            if self.num_scaler:
                self.num_features = self.num_scaler.transform(num_data)
            else:
                self.num_features = num_data
        else:
            self.num_features = np.zeros((len(self.df), 1))
        
        # 标签
        self.labels = self.df[self.label_col].values.astype(np.float32)
    
    def _tokenize_events(self, events) -> List[int]:
        """将事件序列转换为 Token ID"""
        if isinstance(events, str):
            # 字符串格式: "event1,event2,event3" 或 JSON
            try:
                events = json.loads(events)
            except json.JSONDecodeError:
                events = events.split(',')
        
        if not isinstance(events, (list, tuple)):
            events = []
        
        # 转换为 Token IDs
        token_ids = [
            EVENT_VOCAB.get(str(e).lower().strip(), EVENT_VOCAB["<UNK>"])
            for e in events
        ]
        
        # Pad/Truncate
        if len(token_ids) >= self.max_seq_len:
            return token_ids[-self.max_seq_len:]
        else:
            padding = [EVENT_VOCAB["<PAD>"]] * (self.max_seq_len - len(token_ids))
            return padding + token_ids
    
    def __len__(self) -> int:
        return len(self.df)
    
    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        return {
            'event_seq': torch.tensor(self.event_sequences[idx], dtype=torch.long),
            'static_categorical': torch.tensor(self.cat_features[idx], dtype=torch.long),
            'static_numerical': torch.tensor(self.num_features[idx], dtype=torch.float32),
            'label': torch.tensor(self.labels[idx], dtype=torch.float32),
        }
    
    def get_transforms(self) -> Tuple[Dict[str, LabelEncoder], StandardScaler]:
        """获取编码器和归一化器 (用于验证集)"""
        return self.cat_encoders, self.num_scaler


# =============================================================================
# 训练核心
# =============================================================================
def train_one_epoch(
    model: nn.Module,
    dataloader: DataLoader,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    device: torch.device,
) -> float:
    """
    训练一个 Epoch
    
    Returns:
        平均训练损失
    """
    model.train()
    total_loss = 0.0
    num_batches = 0
    
    for batch in dataloader:
        # 移动到设备
        event_seq = batch['event_seq'].to(device)
        static_cat = batch['static_categorical'].to(device)
        static_num = batch['static_numerical'].to(device)
        labels = batch['label'].to(device).unsqueeze(1)
        
        # 前向传播
        optimizer.zero_grad()
        outputs = model(event_seq, static_cat, static_num)
        loss = criterion(outputs, labels)
        
        # 反向传播
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        
        total_loss += loss.item()
        num_batches += 1
    
    return total_loss / max(num_batches, 1)


def evaluate(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> Tuple[float, float]:
    """
    验证模型
    
    Returns:
        (平均损失, AUC)
    """
    model.eval()
    total_loss = 0.0
    num_batches = 0
    all_preds = []
    all_labels = []
    
    with torch.no_grad():
        for batch in dataloader:
            event_seq = batch['event_seq'].to(device)
            static_cat = batch['static_categorical'].to(device)
            static_num = batch['static_numerical'].to(device)
            labels = batch['label'].to(device).unsqueeze(1)
            
            outputs = model(event_seq, static_cat, static_num)
            loss = criterion(outputs, labels)
            
            total_loss += loss.item()
            num_batches += 1
            
            all_preds.extend(outputs.cpu().numpy().flatten())
            all_labels.extend(labels.cpu().numpy().flatten())
    
    avg_loss = total_loss / max(num_batches, 1)
    
    # 计算 AUC
    try:
        auc = roc_auc_score(all_labels, all_preds)
    except ValueError:
        auc = 0.5  # 如果标签全为一类
    
    return avg_loss, auc


class EarlyStopping:
    """
    Early Stopping 机制
    
    当验证指标连续 patience 个 Epoch 未改善时，停止训练。
    """
    
    def __init__(self, patience: int = 5, min_delta: float = 0.001, mode: str = 'max'):
        """
        Args:
            patience: 容忍的 Epoch 数
            min_delta: 最小改善幅度
            mode: 'max' (AUC) 或 'min' (Loss)
        """
        self.patience = patience
        self.min_delta = min_delta
        self.mode = mode
        self.counter = 0
        self.best_score = None
        self.early_stop = False
    
    def __call__(self, score: float) -> bool:
        """
        检查是否应该停止
        
        Returns:
            True 如果应该停止
        """
        if self.best_score is None:
            self.best_score = score
            return False
        
        if self.mode == 'max':
            improved = score > self.best_score + self.min_delta
        else:
            improved = score < self.best_score - self.min_delta
        
        if improved:
            self.best_score = score
            self.counter = 0
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.early_stop = True
        
        return self.early_stop


def save_model(
    model: nn.Module,
    config: Dict[str, Any],
    output_dir: str,
    best_auc: float,
):
    """
    保存模型权重和配置
    
    Args:
        model: 训练好的模型
        config: 模型架构参数
        output_dir: 输出目录
        best_auc: 最佳 AUC
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存模型权重
    model_path = os.path.join(output_dir, 'model.pt')
    torch.save(model.state_dict(), model_path)
    logger.info(f"模型权重已保存: {model_path}")
    
    # 保存模型配置
    config['best_auc'] = best_auc
    config['saved_at'] = datetime.now().isoformat()
    
    config_path = os.path.join(output_dir, 'model_config.json')
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    logger.info(f"模型配置已保存: {config_path}")


# =============================================================================
# 主函数
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description='SentinEL Multimodal Churn Transformer 训练脚本')
    
    # 数据参数
    parser.add_argument('--data_path', type=str, required=True, help='训练数据路径 (CSV)')
    parser.add_argument('--val_data_path', type=str, default=None, help='验证数据路径 (CSV)')
    parser.add_argument('--val_split', type=float, default=0.2, help='验证集比例 (如果未提供 val_data_path)')
    
    # 特征列配置
    parser.add_argument('--event_col', type=str, default='event_sequence', help='事件序列列名')
    parser.add_argument('--cat_cols', type=str, nargs='+', default=['country', 'device_type', 'membership'],
                       help='类别特征列名')
    parser.add_argument('--num_cols', type=str, nargs='+', 
                       default=['rage_clicks_5m', 'policy_views_5m', 'cart_additions_5m', 
                               'active_session_duration', 'total_events'],
                       help='数值特征列名')
    parser.add_argument('--label_col', type=str, default='churned', help='标签列名')
    
    # 模型参数 (支持 Vertex AI Vizier 调参)
    parser.add_argument('--d_model', type=int, default=64, help='Transformer 嵌入维度')
    parser.add_argument('--nhead', type=int, default=4, help='注意力头数')
    parser.add_argument('--num_layers', type=int, default=2, help='Transformer 层数')
    parser.add_argument('--ff_dim', type=int, default=256, help='前馈网络维度')
    parser.add_argument('--dropout', type=float, default=0.1, help='Dropout 比率')
    parser.add_argument('--max_seq_len', type=int, default=20, help='最大序列长度')
    parser.add_argument('--vocab_size', type=int, default=30, help='词汇表大小')
    
    # 类别特征维度 (根据实际数据调整)
    parser.add_argument('--cat_feature_dims', type=int, nargs='+', default=[200, 10, 5],
                       help='每个类别特征的可选值数量')
    parser.add_argument('--cat_embed_dim', type=int, default=8, help='类别特征嵌入维度')
    parser.add_argument('--feature_hidden_dim', type=int, default=64, help='特征塔隐藏层维度')
    parser.add_argument('--feature_output_dim', type=int, default=64, help='特征塔输出维度')
    parser.add_argument('--fusion_hidden_dim', type=int, default=128, help='融合层隐藏维度')
    
    # 训练参数
    parser.add_argument('--epochs', type=int, default=50, help='训练轮数')
    parser.add_argument('--batch_size', type=int, default=64, help='批次大小')
    parser.add_argument('--lr', type=float, default=0.001, help='学习率')
    parser.add_argument('--weight_decay', type=float, default=0.01, help='权重衰减')
    parser.add_argument('--patience', type=int, default=5, help='Early Stopping 耐心值')
    
    # 输出参数
    parser.add_argument('--output_dir', type=str, default='./output', help='模型输出目录')
    
    # Vertex AI 参数
    parser.add_argument('--experiment_name', type=str, default='sentinel-churn-v2', help='Vertex AI 实验名称')
    parser.add_argument('--run_name', type=str, default=None, help='运行名称')
    parser.add_argument('--enable_vertex', action='store_true', help='启用 Vertex AI Experiments')
    parser.add_argument('--project_id', type=str, default='sentinel-ai-project-482208', help='GCP 项目 ID')
    parser.add_argument('--location', type=str, default='us-central1', help='GCP 区域')
    
    args = parser.parse_args()
    
    # ========== 初始化 Vertex AI ==========
    aiplatform = None
    if args.enable_vertex:
        try:
            from google.cloud import aiplatform as aip
            aiplatform = aip
            aiplatform.init(
                project=args.project_id,
                location=args.location,
                experiment=args.experiment_name,
            )
            run_name = args.run_name or f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            aiplatform.start_run(run_name)
            logger.info(f"Vertex AI Experiment 已启动: {args.experiment_name}/{run_name}")
        except ImportError:
            logger.warning("google-cloud-aiplatform 未安装，跳过 Vertex AI 集成")
            aiplatform = None
        except Exception as e:
            logger.warning(f"Vertex AI 初始化失败: {e}")
            aiplatform = None
    
    # ========== 记录参数 ==========
    params = vars(args)
    logger.info("训练参数:")
    for key, value in params.items():
        logger.info(f"  {key}: {value}")
    
    if aiplatform:
        try:
            aiplatform.log_params(params)
        except Exception as e:
            logger.warning(f"记录参数到 Vertex AI 失败: {e}")
    
    # ========== 设备配置 ==========
    if torch.cuda.is_available():
        device_str = 'cuda'
    elif torch.backends.mps.is_available() and torch.backends.mps.is_built():
        device_str = 'mps'
    else:
        device_str = 'cpu'
    
    device = torch.device(device_str)
    logger.info(f"使用设备: {device}")
    
    # ========== 加载数据 ==========
    logger.info(f"加载训练数据: {args.data_path}")
    try:
        train_df = pd.read_csv(args.data_path)
    except Exception as e:
        logger.error(f"加载训练数据失败: {e}")
        raise
    
    # 分割验证集
    if args.val_data_path:
        logger.info(f"加载验证数据: {args.val_data_path}")
        val_df = pd.read_csv(args.val_data_path)
    else:
        from sklearn.model_selection import train_test_split
        train_df, val_df = train_test_split(
            train_df, test_size=args.val_split, random_state=42, stratify=train_df[args.label_col]
        )
        logger.info(f"自动分割验证集 (比例: {args.val_split})")
    
    logger.info(f"训练集大小: {len(train_df)} | 验证集大小: {len(val_df)}")
    
    # ========== 创建数据集 ==========
    # 确定数值特征列 (过滤掉不存在的列)
    available_num_cols = [col for col in args.num_cols if col in train_df.columns]
    available_cat_cols = [col for col in args.cat_cols if col in train_df.columns]
    
    if not available_num_cols:
        logger.warning(f"指定的数值特征列均不存在，使用空数值特征")
        # 创建虚拟数值列
        train_df['_dummy_num'] = 0.0
        val_df['_dummy_num'] = 0.0
        available_num_cols = ['_dummy_num']
    
    if not available_cat_cols:
        logger.warning(f"指定的类别特征列均不存在，使用空类别特征")
        train_df['_dummy_cat'] = 'default'
        val_df['_dummy_cat'] = 'default'
        available_cat_cols = ['_dummy_cat']
    
    num_numerical_features = len(available_num_cols)
    
    # 动态计算类别特征维度
    cat_feature_dims = []
    for col in available_cat_cols:
        unique_count = train_df[col].nunique() + 1  # +1 for unknown
        cat_feature_dims.append(min(unique_count, 1000))  # 限制最大为 1000
    
    logger.info(f"类别特征: {available_cat_cols} | 维度: {cat_feature_dims}")
    logger.info(f"数值特征: {available_num_cols}")
    
    train_dataset = MultimodalChurnDataset(
        df=train_df,
        event_col=args.event_col,
        cat_cols=available_cat_cols,
        num_cols=available_num_cols,
        label_col=args.label_col,
        max_seq_len=args.max_seq_len,
        fit_transforms=True,
    )
    
    cat_encoders, num_scaler = train_dataset.get_transforms()
    
    val_dataset = MultimodalChurnDataset(
        df=val_df,
        event_col=args.event_col,
        cat_cols=available_cat_cols,
        num_cols=available_num_cols,
        label_col=args.label_col,
        max_seq_len=args.max_seq_len,
        cat_encoders=cat_encoders,
        num_scaler=num_scaler,
        fit_transforms=False,
    )
    
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False, num_workers=0)
    
    # ========== 创建模型 ==========
    model_config = {
        'vocab_size': args.vocab_size,
        'seq_embed_dim': args.d_model,
        'num_heads': args.nhead,
        'num_transformer_layers': args.num_layers,
        'ff_dim': args.ff_dim,
        'max_seq_len': args.max_seq_len,
        'cat_feature_dims': cat_feature_dims,
        'cat_embed_dim': args.cat_embed_dim,
        'num_numerical_features': num_numerical_features,
        'feature_hidden_dim': args.feature_hidden_dim,
        'feature_output_dim': args.feature_output_dim,
        'dropout': args.dropout,
        'fusion_hidden_dim': args.fusion_hidden_dim,
    }
    
    model = MultimodalChurnTransformer(**model_config)
    model.to(device)
    
    num_params = sum(p.numel() for p in model.parameters())
    logger.info(f"模型参数量: {num_params:,}")
    
    # ========== 优化器和损失函数 ==========
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    criterion = nn.BCELoss()
    
    # 学习率调度器
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='max', factor=0.5, patience=2
    )
    
    # Early Stopping
    early_stopping = EarlyStopping(patience=args.patience, mode='max')
    
    # ========== 训练循环 ==========
    best_auc = 0.0
    best_epoch = 0
    
    logger.info("开始训练...")
    for epoch in range(args.epochs):
        start_time = time.time()
        
        # 训练
        train_loss = train_one_epoch(model, train_loader, optimizer, criterion, device)
        
        # 验证
        val_loss, val_auc = evaluate(model, val_loader, criterion, device)
        
        epoch_time = time.time() - start_time
        
        # 更新学习率
        scheduler.step(val_auc)
        current_lr = optimizer.param_groups[0]['lr']
        
        # 记录指标
        logger.info(
            f"Epoch {epoch + 1}/{args.epochs} | "
            f"Train Loss: {train_loss:.4f} | "
            f"Val Loss: {val_loss:.4f} | "
            f"Val AUC: {val_auc:.4f} | "
            f"LR: {current_lr:.6f} | "
            f"Time: {epoch_time:.1f}s"
        )
        
        # 上报到 Vertex AI
        if aiplatform:
            try:
                aiplatform.log_metrics({
                    'train_loss': train_loss,
                    'val_loss': val_loss,
                    'val_auc': val_auc,
                    'learning_rate': current_lr,
                    'epoch': epoch + 1,
                })
            except Exception as e:
                logger.warning(f"上报指标失败: {e}")
        
        # 保存最佳模型
        if val_auc > best_auc:
            best_auc = val_auc
            best_epoch = epoch + 1
            save_model(model, model_config, args.output_dir, best_auc)
            logger.info(f"✓ 新的最佳模型 (AUC: {best_auc:.4f})")
        
        # Early Stopping 检查
        if early_stopping(val_auc):
            logger.info(f"触发 Early Stopping | 最佳 Epoch: {best_epoch} | 最佳 AUC: {best_auc:.4f}")
            break
    
    # ========== 训练完成 ==========
    logger.info("=" * 60)
    logger.info(f"训练完成!")
    logger.info(f"  最佳 Epoch: {best_epoch}")
    logger.info(f"  最佳 Val AUC: {best_auc:.4f}")
    logger.info(f"  模型保存路径: {args.output_dir}")
    logger.info("=" * 60)
    
    # 记录最终指标
    if aiplatform:
        try:
            aiplatform.log_metrics({
                'best_val_auc': best_auc,
                'best_epoch': best_epoch,
                'total_epochs': epoch + 1,
            })
            aiplatform.end_run()
        except Exception as e:
            logger.warning(f"结束 Vertex AI Run 失败: {e}")


if __name__ == '__main__':
    main()
