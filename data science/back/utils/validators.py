"""
数据验证工具
"""

import re
from typing import Any, Dict, List, Optional
from .exceptions import ValidationError


def validate_email(email: str) -> bool:
    """
    验证邮箱格式
    
    Args:
        email: 邮箱地址
        
    Returns:
        bool: 是否有效
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_file_type(filename: str, allowed_types: List[str]) -> bool:
    """
    验证文件类型
    
    Args:
        filename: 文件名
        allowed_types: 允许的文件扩展名列表（如 ['csv', 'xlsx']）
        
    Returns:
        bool: 是否允许
    """
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in [t.lower() for t in allowed_types]


def validate_file_size(size_bytes: int, max_size_mb: int = 100) -> bool:
    """
    验证文件大小
    
    Args:
        size_bytes: 文件大小（字节）
        max_size_mb: 最大允许大小（MB）
        
    Returns:
        bool: 是否符合要求
    """
    max_bytes = max_size_mb * 1024 * 1024
    return size_bytes <= max_bytes


def require_fields(data: Dict[str, Any], required_fields: List[str]) -> None:
    """
    验证必填字段
    
    Args:
        data: 数据字典
        required_fields: 必填字段列表
        
    Raises:
        ValidationError: 缺少必填字段时抛出
    """
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        raise ValidationError(
            f"Missing required fields: {', '.join(missing_fields)}"
        )


def validate_data_types(data: Dict[str, Any], type_spec: Dict[str, type]) -> None:
    """
    验证数据类型
    
    Args:
        data: 数据字典
        type_spec: 类型规范，格式：{字段名: 期望类型}
        
    Raises:
        ValidationError: 类型不匹配时抛出
    """
    for field, expected_type in type_spec.items():
        if field in data and not isinstance(data[field], expected_type):
            raise ValidationError(
                f"Field '{field}' must be of type {expected_type.__name__}, "
                f"got {type(data[field]).__name__}"
            )


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除不安全字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        str: 清理后的文件名
    """
    # 只保留字母、数字、点、下划线和短横线
    return re.sub(r'[^\w\.-]', '_', filename)


def validate_pagination(page: int, page_size: int, max_page_size: int = 100) -> None:
    """
    验证分页参数
    
    Args:
        page: 页码
        page_size: 每页大小
        max_page_size: 最大每页大小
        
    Raises:
        ValidationError: 参数无效时抛出
    """
    if page < 1:
        raise ValidationError("Page must be >= 1")
    
    if page_size < 1:
        raise ValidationError("Page size must be >= 1")
    
    if page_size > max_page_size:
        raise ValidationError(f"Page size must be <= {max_page_size}")
