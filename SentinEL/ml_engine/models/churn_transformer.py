"""
SentinEL 多模态 Transformer 流失预测模型 (Multimodal Churn Transformer)

下一代核心预测引擎，支持:
    1. 事件序列 (Sequence Tower with Transformer)
    2. 静态类别特征 (Categorical Embeddings)
    3. 静态数值特征 (Numerical Features from Feature Store)

架构:
    ┌──────────────────┐    ┌──────────────────┐
    │  Event Sequence  │    │  Static Features │
    │    (Seq Tower)   │    │  (Feature Tower) │
    │                  │    │                  │
    │  Embedding       │    │  Cat Embedding   │
    │      ↓           │    │      ↓           │
    │  Positional Enc  │    │  Concat + MLP    │
    │      ↓           │    │                  │
    │  TransformerEnc  │    │                  │
    │      ↓           │    │                  │
    │  Attention Pool  │    │                  │
    └────────┬─────────┘    └────────┬─────────┘
             │                       │
             └───────────┬───────────┘
                         │
                   ┌─────┴─────┐
                   │  Fusion   │
                   │   Layer   │
                   └─────┬─────┘
                         │
                   ┌─────┴─────┐
                   │  Sigmoid  │
                   └───────────┘

依赖:
    pip install torch
"""

from typing import Optional, Tuple
import math

import torch
import torch.nn as nn
import torch.nn.functional as F


# =============================================================================
# 位置编码
# =============================================================================
class LearnablePositionalEncoding(nn.Module):
    """
    可学习的位置编码
    
    相比固定正弦编码，在短序列场景下表现更优。
    """
    
    def __init__(self, max_seq_len: int, embed_dim: int):
        super().__init__()
        self.pos_embedding = nn.Embedding(max_seq_len, embed_dim)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch, seq_len, embed_dim)
        Returns:
            (batch, seq_len, embed_dim) 位置编码
        """
        batch_size, seq_len, _ = x.size()
        positions = torch.arange(0, seq_len, device=x.device).unsqueeze(0).expand(batch_size, -1)
        return self.pos_embedding(positions)


class SinusoidalPositionalEncoding(nn.Module):
    """
    正弦波位置编码 (Vaswani et al., 2017)
    
    适用于需要泛化到更长序列的场景。
    """
    
    def __init__(self, max_seq_len: int, embed_dim: int, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)
        
        # 预计算位置编码矩阵
        pe = torch.zeros(max_seq_len, embed_dim)
        position = torch.arange(0, max_seq_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, embed_dim, 2).float() * (-math.log(10000.0) / embed_dim))
        
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)  # (1, max_seq_len, embed_dim)
        
        self.register_buffer('pe', pe)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch, seq_len, embed_dim)
        Returns:
            (batch, seq_len, embed_dim) 位置编码
        """
        seq_len = x.size(1)
        return self.pe[:, :seq_len, :]


# =============================================================================
# 注意力池化
# =============================================================================
class AttentionPooling(nn.Module):
    """
    注意力池化层
    
    使用可学习的查询向量对序列进行加权聚合，
    比简单的 Mean Pooling 能更好地捕捉重要时刻。
    """
    
    def __init__(self, embed_dim: int):
        super().__init__()
        self.query = nn.Parameter(torch.randn(1, 1, embed_dim))
        self.scale = embed_dim ** 0.5
    
    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Args:
            x: (batch, seq_len, embed_dim)
            mask: (batch, seq_len) True 表示需要 mask 的位置
        Returns:
            (batch, embed_dim) 池化后的向量
        """
        batch_size = x.size(0)
        query = self.query.expand(batch_size, -1, -1)  # (batch, 1, embed_dim)
        
        # 计算注意力分数
        scores = torch.bmm(query, x.transpose(1, 2)) / self.scale  # (batch, 1, seq_len)
        
        # 应用 mask
        if mask is not None:
            scores = scores.masked_fill(mask.unsqueeze(1), float('-inf'))
        
        attn_weights = F.softmax(scores, dim=-1)  # (batch, 1, seq_len)
        
        # 加权求和
        pooled = torch.bmm(attn_weights, x)  # (batch, 1, embed_dim)
        return pooled.squeeze(1)  # (batch, embed_dim)


# =============================================================================
# Sequence Tower (Transformer)
# =============================================================================
class SequenceTower(nn.Module):
    """
    序列塔: 使用 Transformer 处理事件序列
    
    架构: Embedding -> Positional Encoding -> TransformerEncoder -> Attention Pooling
    """
    
    def __init__(
        self,
        vocab_size: int = 30,
        embed_dim: int = 64,
        num_heads: int = 4,
        num_layers: int = 2,
        ff_dim: int = 256,
        dropout: float = 0.1,
        max_seq_len: int = 64,
        padding_idx: int = 0,
        use_learnable_pe: bool = True,
    ):
        super().__init__()
        
        if embed_dim % num_heads != 0:
            raise ValueError(f"embed_dim ({embed_dim}) 必须能被 num_heads ({num_heads}) 整除")
        
        self.padding_idx = padding_idx
        self.embed_dim = embed_dim
        
        # 事件嵌入层
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=padding_idx)
        
        # 位置编码
        if use_learnable_pe:
            self.pos_encoding = LearnablePositionalEncoding(max_seq_len, embed_dim)
        else:
            self.pos_encoding = SinusoidalPositionalEncoding(max_seq_len, embed_dim, dropout)
        
        # Transformer Encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim,
            nhead=num_heads,
            dim_feedforward=ff_dim,
            dropout=dropout,
            batch_first=True,
            activation='gelu',
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        # 注意力池化
        self.attention_pool = AttentionPooling(embed_dim)
        
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, event_seq: torch.Tensor) -> torch.Tensor:
        """
        Args:
            event_seq: (batch, seq_len) 事件 ID 序列, dtype long
        Returns:
            (batch, embed_dim) 序列特征向量
        """
        # 嵌入
        token_emb = self.embedding(event_seq)  # (batch, seq, embed_dim)
        pos_emb = self.pos_encoding(token_emb)
        embedded = token_emb + pos_emb
        embedded = self.dropout(embedded)
        
        # Padding Mask: True 表示需要 mask 的位置
        padding_mask = (event_seq == self.padding_idx)
        
        # Transformer 编码
        encoded = self.transformer(embedded, src_key_padding_mask=padding_mask)
        
        # 注意力池化
        pooled = self.attention_pool(encoded, mask=padding_mask)
        
        return pooled


# =============================================================================
# Feature Tower (MLP for Static Features)
# =============================================================================
class FeatureTower(nn.Module):
    """
    特征塔: 处理静态类别特征和数值特征
    
    架构: 
        Categorical -> Embeddings -> Flatten
                                            -> Concat -> MLP
        Numerical -------------------------→
    """
    
    def __init__(
        self,
        cat_feature_dims: list,  # 每个类别特征的 vocab size 列表
        cat_embed_dim: int = 8,
        num_numerical_features: int = 5,
        hidden_dim: int = 64,
        output_dim: int = 64,
        dropout: float = 0.1,
    ):
        """
        Args:
            cat_feature_dims: 每个类别特征的可选值数量，如 [10, 5, 3] 表示 3 个类别特征
            cat_embed_dim: 每个类别特征的嵌入维度
            num_numerical_features: 数值特征数量
            hidden_dim: MLP 隐藏层维度
            output_dim: 输出特征向量维度
            dropout: Dropout 比率
        """
        super().__init__()
        
        self.num_cat_features = len(cat_feature_dims)
        self.num_numerical_features = num_numerical_features
        
        # 类别特征嵌入层
        self.cat_embeddings = nn.ModuleList([
            nn.Embedding(dim, cat_embed_dim) for dim in cat_feature_dims
        ])
        
        # 输入维度 = 类别嵌入总维度 + 数值特征维度
        cat_total_dim = self.num_cat_features * cat_embed_dim
        mlp_input_dim = cat_total_dim + num_numerical_features
        
        # MLP
        self.mlp = nn.Sequential(
            nn.Linear(mlp_input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, output_dim),
            nn.BatchNorm1d(output_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
        )
    
    def forward(
        self, 
        static_categorical: torch.Tensor, 
        static_numerical: torch.Tensor
    ) -> torch.Tensor:
        """
        Args:
            static_categorical: (batch, num_cat_features) 类别特征索引, dtype long
            static_numerical: (batch, num_num_features) 数值特征, dtype float
        Returns:
            (batch, output_dim) 特征向量
        """
        # 类别特征嵌入
        cat_embeds = []
        for i, emb_layer in enumerate(self.cat_embeddings):
            cat_embeds.append(emb_layer(static_categorical[:, i]))
        
        # 拼接类别嵌入
        cat_concat = torch.cat(cat_embeds, dim=-1)  # (batch, num_cat * cat_embed_dim)
        
        # 拼接数值特征
        features = torch.cat([cat_concat, static_numerical], dim=-1)
        
        # MLP
        return self.mlp(features)


# =============================================================================
# 多模态融合 Transformer 模型
# =============================================================================
class MultimodalChurnTransformer(nn.Module):
    """
    多模态流失预测 Transformer
    
    融合三种输入:
        1. event_seq: 事件 ID 序列 (Sequence Tower)
        2. static_categorical: 类别特征 (Feature Tower)
        3. static_numerical: 数值特征 (Feature Tower)
    
    输出: 流失概率 [0, 1]
    """
    
    def __init__(
        self,
        # Sequence Tower 参数
        vocab_size: int = 30,
        seq_embed_dim: int = 64,
        num_heads: int = 4,
        num_transformer_layers: int = 2,
        ff_dim: int = 256,
        max_seq_len: int = 64,
        padding_idx: int = 0,
        use_learnable_pe: bool = True,
        # Feature Tower 参数
        cat_feature_dims: list = None,  # 如 [10, 5, 3]
        cat_embed_dim: int = 8,
        num_numerical_features: int = 5,
        feature_hidden_dim: int = 64,
        feature_output_dim: int = 64,
        # 通用参数
        dropout: float = 0.1,
        # 融合层参数
        fusion_hidden_dim: int = 128,
    ):
        super().__init__()
        
        # 默认类别特征维度
        if cat_feature_dims is None:
            cat_feature_dims = [10, 5, 3]  # 默认: 国家(10), 设备类型(5), 会员等级(3)
        
        self.seq_embed_dim = seq_embed_dim
        self.feature_output_dim = feature_output_dim
        
        # ========== Sequence Tower ==========
        self.sequence_tower = SequenceTower(
            vocab_size=vocab_size,
            embed_dim=seq_embed_dim,
            num_heads=num_heads,
            num_layers=num_transformer_layers,
            ff_dim=ff_dim,
            dropout=dropout,
            max_seq_len=max_seq_len,
            padding_idx=padding_idx,
            use_learnable_pe=use_learnable_pe,
        )
        
        # ========== Feature Tower ==========
        self.feature_tower = FeatureTower(
            cat_feature_dims=cat_feature_dims,
            cat_embed_dim=cat_embed_dim,
            num_numerical_features=num_numerical_features,
            hidden_dim=feature_hidden_dim,
            output_dim=feature_output_dim,
            dropout=dropout,
        )
        
        # ========== Fusion Layer ==========
        fusion_input_dim = seq_embed_dim + feature_output_dim
        
        self.fusion = nn.Sequential(
            nn.Linear(fusion_input_dim, fusion_hidden_dim),
            nn.LayerNorm(fusion_hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(fusion_hidden_dim, fusion_hidden_dim // 2),
            nn.LayerNorm(fusion_hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
        )
        
        # ========== Classification Head ==========
        self.classifier = nn.Linear(fusion_hidden_dim // 2, 1)
        self.sigmoid = nn.Sigmoid()
        
        # 权重初始化
        self._init_weights()
    
    def _init_weights(self):
        """
        权重初始化
        
        - Linear: Xavier 均匀初始化
        - LayerNorm: 常数初始化 (weight=1, bias=0)
        - Embedding: 正态初始化
        """
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.LayerNorm):
                nn.init.ones_(module.weight)
                nn.init.zeros_(module.bias)
            elif isinstance(module, nn.Embedding):
                nn.init.normal_(module.weight, mean=0, std=0.02)
                if module.padding_idx is not None:
                    nn.init.zeros_(module.weight[module.padding_idx])
    
    def forward(
        self,
        event_seq: torch.Tensor,
        static_categorical: torch.Tensor,
        static_numerical: torch.Tensor,
    ) -> torch.Tensor:
        """
        前向传播
        
        Args:
            event_seq: (batch, seq_len) 事件 ID 序列, dtype long
            static_categorical: (batch, num_cat_features) 类别特征索引, dtype long
            static_numerical: (batch, num_num_features) 数值特征, dtype float
            
        Returns:
            (batch, 1) 流失概率 [0, 1]
        """
        # Sequence Tower
        seq_features = self.sequence_tower(event_seq)  # (batch, seq_embed_dim)
        
        # Feature Tower
        static_features = self.feature_tower(static_categorical, static_numerical)  # (batch, feature_output_dim)
        
        # Fusion
        fused = torch.cat([seq_features, static_features], dim=-1)  # (batch, seq_embed_dim + feature_output_dim)
        fused = self.fusion(fused)
        
        # Classification
        logits = self.classifier(fused)
        probability = self.sigmoid(logits)
        
        return probability
    
    def get_sequence_embedding(self, event_seq: torch.Tensor) -> torch.Tensor:
        """
        获取序列嵌入 (用于可视化或下游任务)
        
        Args:
            event_seq: (batch, seq_len)
        Returns:
            (batch, seq_embed_dim)
        """
        return self.sequence_tower(event_seq)


# =============================================================================
# 工厂函数
# =============================================================================
def create_model(
    model_type: str = "multimodal_transformer",
    **kwargs
) -> nn.Module:
    """
    模型工厂函数
    
    Args:
        model_type: 模型类型，支持 "multimodal_transformer" 或 "transformer"
        **kwargs: 模型参数
        
    Returns:
        nn.Module: 模型实例
    """
    model_type_lower = model_type.lower()
    
    if model_type_lower in ["multimodal_transformer", "multimodal", "mm_transformer"]:
        return MultimodalChurnTransformer(**kwargs)
    elif model_type_lower == "transformer":
        # 兼容旧版单模态 Transformer
        from ml_engine.models.churn_transformer import ChurnTransformer
        return ChurnTransformer(**kwargs)
    else:
        raise ValueError(f"不支持的模型类型: {model_type}. 支持: multimodal_transformer, transformer")


# =============================================================================
# 冒烟测试 (Sanity Check)
# =============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("MultimodalChurnTransformer 冒烟测试")
    print("=" * 60)
    
    # 配置
    batch_size = 8
    seq_len = 20
    vocab_size = 30
    num_cat_features = 3
    cat_feature_dims = [10, 5, 3]  # 国家, 设备类型, 会员等级
    num_numerical_features = 5    # 来自 Feature Store 的实时统计特征
    
    # 创建模型
    model = MultimodalChurnTransformer(
        vocab_size=vocab_size,
        seq_embed_dim=64,
        num_heads=4,
        num_transformer_layers=2,
        ff_dim=256,
        max_seq_len=seq_len,
        cat_feature_dims=cat_feature_dims,
        cat_embed_dim=8,
        num_numerical_features=num_numerical_features,
        feature_hidden_dim=64,
        feature_output_dim=64,
        dropout=0.1,
        fusion_hidden_dim=128,
    )
    
    print(f"\n模型参数量: {sum(p.numel() for p in model.parameters()):,}")
    
    # 生成 Dummy Tensors
    print("\n输入张量形状:")
    
    # 1. 事件序列 (随机 token ids)
    event_seq = torch.randint(0, vocab_size, (batch_size, seq_len))
    print(f"  event_seq:          {event_seq.shape} (dtype: {event_seq.dtype})")
    
    # 2. 静态类别特征
    static_categorical = torch.stack([
        torch.randint(0, dim, (batch_size,)) for dim in cat_feature_dims
    ], dim=1)
    print(f"  static_categorical: {static_categorical.shape} (dtype: {static_categorical.dtype})")
    
    # 3. 静态数值特征 (模拟 Feature Store 数据)
    static_numerical = torch.randn(batch_size, num_numerical_features)
    print(f"  static_numerical:   {static_numerical.shape} (dtype: {static_numerical.dtype})")
    
    # 前向传播
    model.eval()
    with torch.no_grad():
        output = model(event_seq, static_categorical, static_numerical)
    
    print(f"\n输出张量形状:")
    print(f"  output:             {output.shape} (dtype: {output.dtype})")
    print(f"  输出值范围:          [{output.min().item():.4f}, {output.max().item():.4f}]")
    
    # 验证
    assert output.shape == (batch_size, 1), f"输出形状错误: 期望 ({batch_size}, 1), 实际 {output.shape}"
    assert output.min() >= 0 and output.max() <= 1, "输出值超出 [0, 1] 范围"
    
    print("\n" + "=" * 60)
    print("✅ 冒烟测试通过! 网络连通性验证成功。")
    print("=" * 60)
    
    # 测试工厂函数
    print("\n测试工厂函数...")
    model2 = create_model("multimodal_transformer", vocab_size=30)
    print(f"  工厂创建模型: {type(model2).__name__}")
    print("✅ 工厂函数测试通过!")
