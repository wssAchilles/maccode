"""
Model factory exports for SentinEL churn/recommendation models.
"""

from .churn_lstm import ChurnLSTM
from .churn_transformer import ChurnTransformer


def create_model(model_type: str = "lstm", vocab_size: int = 30, **kwargs):
    """
    Unified factory to create churn prediction models.
    """
    if model_type.lower() == "lstm":
        return ChurnLSTM(vocab_size=vocab_size, **kwargs)
    elif model_type.lower() == "transformer":
        return ChurnTransformer(vocab_size=vocab_size, **kwargs)
    else:
        raise ValueError(f"不支持的模型类型: {model_type}")


__all__ = [
    "ChurnLSTM",
    "ChurnTransformer",
    "create_model",
]
