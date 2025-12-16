"""
密钥管理服务模块 - 统一的密钥获取接口
Secrets Management Service

支持两种模式:
1. 本地开发: 从环境变量读取
2. GAE 生产环境: 从 Google Secret Manager 读取

使用示例:
    from services.secrets import get_secret
    api_key = get_secret('OPENWEATHER_API_KEY')
"""

import os
from functools import lru_cache
from typing import Optional


def _is_gae_environment() -> bool:
    """
    检测是否在 Google App Engine 环境中运行
    
    Returns:
        bool: 如果在 GAE 环境中返回 True
    """
    return bool(os.getenv('GAE_ENV') or os.getenv('K_SERVICE'))


def _get_secret_from_secret_manager(secret_id: str, project_id: str) -> Optional[str]:
    """
    从 Google Secret Manager 获取密钥
    
    Args:
        secret_id: 密钥 ID
        project_id: GCP 项目 ID
        
    Returns:
        密钥值，如果失败返回 None
    """
    try:
        from google.cloud import secretmanager
        
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except ImportError:
        print(f"⚠️  google-cloud-secret-manager 未安装，无法从 Secret Manager 获取 {secret_id}")
        return None
    except Exception as e:
        # 静默失败，回退到环境变量
        print(f"⚠️  从 Secret Manager 获取 {secret_id} 失败: {e}")
        return None


@lru_cache(maxsize=32)
def get_secret(secret_id: str, default: Optional[str] = None) -> Optional[str]:
    """
    获取密钥（统一接口）
    
    优先级:
    1. 本地开发环境 -> 直接读取环境变量
    2. GAE 生产环境 -> 尝试 Secret Manager，失败则回退到环境变量
    
    Args:
        secret_id: 密钥 ID (与环境变量名相同)
        default: 默认值（如果密钥不存在）
        
    Returns:
        密钥值
    """
    # 本地开发时直接用环境变量
    if not _is_gae_environment():
        return os.getenv(secret_id, default)
    
    # GAE 生产环境: 尝试从 Secret Manager 读取
    project_id = os.getenv('GCP_PROJECT_ID', 'data-science-44398')
    
    secret_value = _get_secret_from_secret_manager(secret_id, project_id)
    
    if secret_value is not None:
        return secret_value
    
    # 回退到环境变量
    return os.getenv(secret_id, default)


def clear_cache():
    """
    清除密钥缓存（用于测试或密钥轮换后）
    """
    get_secret.cache_clear()
