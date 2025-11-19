"""
数据模型和 Schema 定义
用于 API 请求/响应的数据验证
"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime


@dataclass
class User:
    """用户模型"""
    uid: str
    email: str
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    email_verified: bool = False
    created_at: Optional[datetime] = None


@dataclass
class FileMetadata:
    """文件元数据模型"""
    file_id: str
    filename: str
    content_type: str
    size_bytes: int
    storage_path: str
    owner_uid: str
    uploaded_at: datetime
    public_url: Optional[str] = None


@dataclass
class DatasetInfo:
    """数据集信息模型"""
    dataset_id: str
    name: str
    description: Optional[str]
    file_ids: List[str]
    owner_uid: str
    created_at: datetime
    updated_at: datetime
    row_count: Optional[int] = None
    column_count: Optional[int] = None


@dataclass
class ModelInfo:
    """机器学习模型信息"""
    model_id: str
    name: str
    model_type: str  # 'classification', 'regression', 'clustering', etc.
    description: Optional[str]
    training_dataset_id: str
    model_path: str  # Cloud Storage 路径
    metrics: dict  # 训练指标
    owner_uid: str
    created_at: datetime
    version: str = "1.0.0"


@dataclass
class PredictionRequest:
    """预测请求模型"""
    model_id: str
    input_data: dict  # 输入特征数据
    
    
@dataclass
class PredictionResponse:
    """预测响应模型"""
    prediction_id: str
    model_id: str
    prediction: any  # 预测结果
    confidence: Optional[float] = None
    created_at: Optional[datetime] = None
