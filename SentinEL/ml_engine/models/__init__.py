"""
Model factory exports for SentinEL churn/recommendation models.
"""

from .churn_lstm import ChurnLSTM
from .churn_transformer import MultimodalChurnTransformer

# 向后兼容别名
ChurnTransformer = MultimodalChurnTransformer


def create_model(model_type: str = "lstm", vocab_size: int = 30, **kwargs):
    """
    Unified factory to create churn prediction models.
    
    Args:
        model_type: "lstm", "transformer", 或 "multimodal_transformer"
        vocab_size: 词汇表大小
        **kwargs: 模型特定参数
    """
    model_type_lower = model_type.lower()
    
    if model_type_lower == "lstm":
        return ChurnLSTM(vocab_size=vocab_size, **kwargs)
    elif model_type_lower in ["transformer", "multimodal_transformer", "multimodal"]:
        return MultimodalChurnTransformer(vocab_size=vocab_size, **kwargs)
    else:
        raise ValueError(f"不支持的模型类型: {model_type}")


__all__ = [
    "ChurnLSTM",
    "ChurnTransformer",
    "MultimodalChurnTransformer",
    "create_model",
]

