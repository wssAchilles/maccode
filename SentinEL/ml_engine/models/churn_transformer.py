"""
SentinEL Transformer 流失预测模型

使用自注意力捕捉长程依赖，作为 LSTM 基线的强化版本。

架构:
    Input (token ids) -> Embedding + PositionalEncoding -> TransformerEncoder
    -> Masked Mean Pooling -> FC -> Sigmoid
"""

from typing import Optional

import torch
import torch.nn as nn


class PositionalEncoding(nn.Module):
    """
    可学习的位置编码，避免固定正弦编码在短序列场景下的精度损失。
    """

    def __init__(self, max_seq_len: int, embed_dim: int):
        super().__init__()
        self.pos_embedding = nn.Embedding(max_seq_len, embed_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch, seq_len, embed_dim) — 仅用于读取 seq_len
        Returns:
            (batch, seq_len, embed_dim) 位置编码
        """
        batch_size, seq_len, _ = x.size()
        positions = torch.arange(0, seq_len, device=x.device).unsqueeze(0).expand(batch_size, -1)
        return self.pos_embedding(positions)


class ChurnTransformer(nn.Module):
    """
    Transformer Encoder 流失预测模型
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
    ):
        super().__init__()
        if embed_dim % num_heads != 0:
            raise ValueError("embed_dim 必须能被 num_heads 整除")

        self.padding_idx = padding_idx
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=padding_idx)
        self.pos_encoding = PositionalEncoding(max_seq_len=max_seq_len, embed_dim=embed_dim)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim,
            nhead=num_heads,
            dim_feedforward=ff_dim,
            dropout=dropout,
            batch_first=True,
            activation="gelu",
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(embed_dim, 1)
        self.sigmoid = nn.Sigmoid()

        self._reset_parameters()

    def _reset_parameters(self) -> None:
        nn.init.xavier_uniform_(self.fc.weight)
        nn.init.zeros_(self.fc.bias)

    def forward(self, x: torch.Tensor, lengths: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Args:
            x: (batch, seq_len) token ids
            lengths: optional (batch,) 实际长度
        Returns:
            (batch, 1) 概率
        """
        batch_size, seq_len = x.size()
        token_emb = self.embedding(x)  # (batch, seq, embed_dim)
        pos_emb = self.pos_encoding(token_emb)
        embedded = token_emb + pos_emb

        # padding mask: True 为需要 mask 的 PAD 位置
        padding_mask = (x == self.padding_idx)

        encoded = self.transformer(embedded, src_key_padding_mask=padding_mask)

        # Masked mean pooling
        mask_expanded = (~padding_mask).unsqueeze(-1).float()
        sum_encoded = (encoded * mask_expanded).sum(dim=1)
        denom = mask_expanded.sum(dim=1).clamp(min=1.0)
        pooled = sum_encoded / denom

        logits = self.fc(self.dropout(pooled))
        return self.sigmoid(logits)


def create_model(
    model_type: str = "transformer",
    vocab_size: int = 30,
    **kwargs,
) -> nn.Module:
    """
    工厂函数（仅创建 Transformer，保持与 LSTM 工厂接口一致）
    """
    if model_type.lower() != "transformer":
        raise ValueError(f"本工厂仅支持 transformer，收到: {model_type}")
    return ChurnTransformer(vocab_size=vocab_size, **kwargs)
