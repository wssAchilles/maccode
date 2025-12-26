"""
SentinEL 流失预测 LSTM 模型
基于 PyTorch 的时序深度学习模型，用于捕捉用户行为序列中的流失信号

架构:
    Input -> Embedding -> LSTM -> Dropout -> FC -> Sigmoid

输入张量形状:
    (batch_size, seq_length) - 事件 Token ID 序列

输出张量形状:
    (batch_size, 1) - 流失概率 (0.0 - 1.0)

使用方法:
    model = ChurnLSTM(vocab_size=30, embed_dim=64, hidden_dim=128)
    output = model(input_tensor)  # shape: (batch, 1)

依赖:
    pip install torch
"""

import torch
import torch.nn as nn
from typing import Tuple, Optional


class ChurnLSTM(nn.Module):
    """
    LSTM 流失预测模型
    
    通过 Embedding 层将离散的事件 ID 映射为稠密向量,
    然后使用双向 LSTM 捕捉时序依赖关系,
    最后通过全连接层输出流失概率。
    
    Attributes:
        vocab_size: 事件词汇表大小 (包含 PAD 和 UNK)
        embed_dim: Embedding 向量维度
        hidden_dim: LSTM 隐藏层维度
        num_layers: LSTM 层数
        dropout: Dropout 概率
        bidirectional: 是否使用双向 LSTM
    """
    
    def __init__(
        self,
        vocab_size: int = 30,
        embed_dim: int = 64,
        hidden_dim: int = 128,
        num_layers: int = 2,
        dropout: float = 0.3,
        bidirectional: bool = True,
        padding_idx: int = 0
    ):
        """
        初始化 LSTM 模型
        
        Args:
            vocab_size: 词汇表大小，默认 30
            embed_dim: Embedding 维度，默认 64
            hidden_dim: LSTM 隐藏层维度，默认 128
            num_layers: LSTM 层数，默认 2
            dropout: Dropout 概率，默认 0.3
            bidirectional: 是否双向 LSTM，默认 True
            padding_idx: PAD token 的索引，默认 0
        """
        super(ChurnLSTM, self).__init__()
        
        self.vocab_size = vocab_size
        self.embed_dim = embed_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.bidirectional = bidirectional
        self.num_directions = 2 if bidirectional else 1
        
        # ==== Embedding 层 ====
        # 将离散的事件 ID 映射为稠密向量
        # padding_idx=0 确保 PAD token 的 embedding 始终为零向量
        self.embedding = nn.Embedding(
            num_embeddings=vocab_size,
            embedding_dim=embed_dim,
            padding_idx=padding_idx
        )
        
        # ==== LSTM 层 ====
        # 处理时序依赖关系
        # batch_first=True: 输入形状为 (batch, seq, feature)
        self.lstm = nn.LSTM(
            input_size=embed_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,  # 仅多层时启用 dropout
            bidirectional=bidirectional
        )
        
        # ==== Dropout 层 ====
        self.dropout = nn.Dropout(dropout)
        
        # ==== 全连接层 ====
        # 输入维度 = hidden_dim * num_directions (双向时翻倍)
        # 输出维度 = 1 (流失概率)
        fc_input_dim = hidden_dim * self.num_directions
        self.fc = nn.Linear(fc_input_dim, 1)
        
        # ==== 激活函数 ====
        self.sigmoid = nn.Sigmoid()
        
        # 初始化权重
        self._init_weights()
    
    def _init_weights(self):
        """
        初始化模型权重
        使用 Xavier 均匀初始化全连接层
        """
        nn.init.xavier_uniform_(self.fc.weight)
        nn.init.zeros_(self.fc.bias)
    
    def forward(
        self, 
        x: torch.Tensor,
        lengths: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        前向传播
        
        Args:
            x: 输入张量, 形状 (batch_size, seq_length)
               包含事件 Token ID 序列
            lengths: 可选，每个序列的实际长度（用于 pack_padded_sequence）
                    形状 (batch_size,)
        
        Returns:
            torch.Tensor: 流失概率, 形状 (batch_size, 1)
                         值域 [0.0, 1.0]
        
        Example:
            >>> model = ChurnLSTM(vocab_size=30)
            >>> x = torch.randint(0, 30, (32, 20))  # batch=32, seq=20
            >>> output = model(x)
            >>> output.shape
            torch.Size([32, 1])
        """
        batch_size = x.size(0)
        
        # 1. Embedding: (batch, seq) -> (batch, seq, embed_dim)
        embedded = self.embedding(x)
        
        # 2. LSTM: (batch, seq, embed_dim) -> (batch, seq, hidden_dim * directions)
        # 如果提供了 lengths，使用 pack_padded_sequence 提高效率
        if lengths is not None:
            # 需要按长度降序排列
            lengths = lengths.cpu()
            packed = nn.utils.rnn.pack_padded_sequence(
                embedded, lengths, batch_first=True, enforce_sorted=False
            )
            lstm_out, (hidden, cell) = self.lstm(packed)
            # 解包
            lstm_out, _ = nn.utils.rnn.pad_packed_sequence(lstm_out, batch_first=True)
        else:
            lstm_out, (hidden, cell) = self.lstm(embedded)
        
        # 3. 提取最后时刻的隐藏状态
        # hidden shape: (num_layers * directions, batch, hidden_dim)
        if self.bidirectional:
            # 拼接最后一层的前向和后向隐藏状态
            # 前向最后层: hidden[-2], 后向最后层: hidden[-1]
            final_hidden = torch.cat((hidden[-2], hidden[-1]), dim=1)
        else:
            # 单向 LSTM，取最后一层
            final_hidden = hidden[-1]
        
        # final_hidden shape: (batch, hidden_dim * directions)
        
        # 4. Dropout
        dropped = self.dropout(final_hidden)
        
        # 5. 全连接层: (batch, hidden_dim * directions) -> (batch, 1)
        logits = self.fc(dropped)
        
        # 6. Sigmoid 激活得到概率
        output = self.sigmoid(logits)
        
        return output
    
    def predict_proba(self, x: torch.Tensor) -> float:
        """
        预测单个样本的流失概率（推理模式）
        
        Args:
            x: 输入张量, 形状 (1, seq_length) 或 (seq_length,)
            
        Returns:
            float: 流失概率 0.0 - 1.0
        """
        self.eval()
        with torch.no_grad():
            if x.dim() == 1:
                x = x.unsqueeze(0)  # 添加 batch 维度
            prob = self.forward(x)
            return prob.item()


class ChurnTransformer(nn.Module):
    """
    Transformer Encoder 流失预测模型（备选方案）
    
    使用自注意力机制捕捉事件序列中的长程依赖关系。
    适用于更长的序列和更复杂的模式。
    
    架构:
        Input -> Embedding + PositionalEncoding -> TransformerEncoder -> MeanPool -> FC
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
        padding_idx: int = 0
    ):
        """
        初始化 Transformer 模型
        
        Args:
            vocab_size: 词汇表大小
            embed_dim: Embedding 维度（必须能被 num_heads 整除）
            num_heads: 注意力头数
            num_layers: Transformer 层数
            ff_dim: Feed-Forward 层维度
            dropout: Dropout 概率
            max_seq_len: 最大序列长度（用于位置编码）
            padding_idx: PAD token 索引
        """
        super(ChurnTransformer, self).__init__()
        
        assert embed_dim % num_heads == 0, "embed_dim 必须能被 num_heads 整除"
        
        self.embed_dim = embed_dim
        self.padding_idx = padding_idx
        
        # Embedding
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=padding_idx)
        
        # 可学习的位置编码
        self.pos_embedding = nn.Embedding(max_seq_len, embed_dim)
        
        # Transformer Encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim,
            nhead=num_heads,
            dim_feedforward=ff_dim,
            dropout=dropout,
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        # 输出层
        self.fc = nn.Linear(embed_dim, 1)
        self.sigmoid = nn.Sigmoid()
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        前向传播
        
        Args:
            x: 输入张量, 形状 (batch_size, seq_length)
            
        Returns:
            torch.Tensor: 流失概率, 形状 (batch_size, 1)
        """
        batch_size, seq_len = x.size()
        
        # 创建位置索引
        positions = torch.arange(0, seq_len, device=x.device).unsqueeze(0).expand(batch_size, -1)
        
        # Embedding + Positional Encoding
        embedded = self.embedding(x) + self.pos_embedding(positions)
        
        # 创建 padding mask
        # True 表示需要被 mask 的位置（即 PAD token）
        padding_mask = (x == self.padding_idx)
        
        # Transformer Encoder
        encoded = self.transformer(embedded, src_key_padding_mask=padding_mask)
        
        # Mean Pooling（忽略 PAD 位置）
        mask_expanded = (~padding_mask).unsqueeze(-1).float()  # (batch, seq, 1)
        sum_encoded = (encoded * mask_expanded).sum(dim=1)  # (batch, embed_dim)
        lengths = mask_expanded.sum(dim=1).clamp(min=1)  # 避免除零
        pooled = sum_encoded / lengths
        
        # 输出
        dropped = self.dropout(pooled)
        logits = self.fc(dropped)
        output = self.sigmoid(logits)
        
        return output


def create_model(
    model_type: str = "lstm",
    vocab_size: int = 30,
    **kwargs
) -> nn.Module:
    """
    工厂函数：创建流失预测模型
    
    Args:
        model_type: 模型类型, "lstm" 或 "transformer"
        vocab_size: 词汇表大小
        **kwargs: 传递给模型构造函数的其他参数
        
    Returns:
        nn.Module: 创建的模型实例
    """
    if model_type.lower() == "lstm":
        return ChurnLSTM(vocab_size=vocab_size, **kwargs)
    elif model_type.lower() == "transformer":
        return ChurnTransformer(vocab_size=vocab_size, **kwargs)
    else:
        raise ValueError(f"不支持的模型类型: {model_type}")


# ==============================================================================
# 测试代码
# ==============================================================================
if __name__ == "__main__":
    # 测试 LSTM 模型
    print("=== 测试 ChurnLSTM ===")
    lstm_model = ChurnLSTM(vocab_size=30, embed_dim=64, hidden_dim=128)
    print(f"模型参数数量: {sum(p.numel() for p in lstm_model.parameters()):,}")
    
    # 随机输入
    test_input = torch.randint(0, 30, (32, 20))  # batch=32, seq=20
    output = lstm_model(test_input)
    print(f"输入形状: {test_input.shape}")
    print(f"输出形状: {output.shape}")
    print(f"输出范围: [{output.min().item():.4f}, {output.max().item():.4f}]")
    
    # 测试 Transformer 模型
    print("\n=== 测试 ChurnTransformer ===")
    transformer_model = ChurnTransformer(vocab_size=30, embed_dim=64)
    print(f"模型参数数量: {sum(p.numel() for p in transformer_model.parameters()):,}")
    
    output_t = transformer_model(test_input)
    print(f"输出形状: {output_t.shape}")
    print(f"输出范围: [{output_t.min().item():.4f}, {output_t.max().item():.4f}]")
    
    # 测试工厂函数
    print("\n=== 测试工厂函数 ===")
    model = create_model("lstm", vocab_size=30)
    print(f"创建模型类型: {type(model).__name__}")
