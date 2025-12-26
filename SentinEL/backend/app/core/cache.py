"""
SentinEL 缓存模块
提供 Redis 缓存支持，实现热点数据毫秒级响应
"""

import os
import json
import time
import logging
import functools
from typing import Optional, Callable, Any

logger = logging.getLogger(__name__)

# Redis 连接配置
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
CACHE_KEY_PREFIX = "sentinel:analysis"


class RedisClient:
    """
    Redis 客户端单例
    支持连接失败时自动降级（Fallback）
    """
    
    _instance: Optional["RedisClient"] = None
    _client = None
    _available: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """初始化 Redis 连接"""
        try:
            import redis
            self._client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )
            # 测试连接
            self._client.ping()
            self._available = True
            logger.info(f"[Cache] Redis 连接成功: {REDIS_HOST}:{REDIS_PORT}")
        except ImportError:
            logger.warning("[Cache] redis 包未安装，缓存功能禁用")
            self._available = False
        except Exception as e:
            logger.warning(f"[Cache] Redis 连接失败，自动降级: {e}")
            self._available = False
    
    @property
    def is_available(self) -> bool:
        """检查 Redis 是否可用"""
        return self._available
    
    def get(self, key: str) -> Optional[dict]:
        """
        获取缓存数据
        
        Args:
            key: 缓存键
        
        Returns:
            缓存的字典数据，或 None（不存在/连接失败）
        """
        if not self._available:
            return None
        
        try:
            data = self._client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning(f"[Cache] 读取缓存失败: {e}")
            return None
    
    def set(self, key: str, value: dict, ttl_seconds: int = 3600) -> bool:
        """
        设置缓存数据
        
        Args:
            key: 缓存键
            value: 要缓存的字典数据
            ttl_seconds: 过期时间（秒）
        
        Returns:
            是否设置成功
        """
        if not self._available:
            return False
        
        try:
            self._client.setex(
                name=key,
                time=ttl_seconds,
                value=json.dumps(value, ensure_ascii=False)
            )
            logger.info(f"[Cache] 缓存已设置: {key} (TTL: {ttl_seconds}s)")
            return True
        except Exception as e:
            logger.warning(f"[Cache] 设置缓存失败: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self._available:
            return False
        
        try:
            self._client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"[Cache] 删除缓存失败: {e}")
            return False


# 全局单例
redis_client = RedisClient()


def cached_analysis(ttl_seconds: int = 3600):
    """
    分析结果缓存装饰器
    
    在执行 analyze_user_workflow 之前检查缓存:
    - Cache Hit: 直接返回缓存数据，注入 data_source="CACHE"
    - Cache Miss: 执行原逻辑，缓存结果，注入 data_source="REALTIME"
    
    Args:
        ttl_seconds: 缓存过期时间（秒），默认 1 小时
    
    Usage:
        @cached_analysis(ttl_seconds=3600)
        def analyze_user_workflow(self, user_id: str, ...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, user_id: str, *args, **kwargs) -> dict:
            # 构建缓存键
            cache_key = f"{CACHE_KEY_PREFIX}:{user_id}"
            
            # 异步 Worker 模式不使用缓存（因为已经进入队列）
            is_async_worker = kwargs.get("is_async_worker", False)
            
            if not is_async_worker:
                # 尝试从缓存获取
                start_time = time.time()
                cached_result = redis_client.get(cache_key)
                
                if cached_result:
                    # Cache Hit
                    cache_time_ms = int((time.time() - start_time) * 1000)
                    cached_result["data_source"] = "CACHE"
                    cached_result["cache_lookup_ms"] = cache_time_ms
                    logger.info(f"[Cache] HIT for user {user_id} ({cache_time_ms}ms)")
                    return cached_result
            
            # Cache Miss - 执行原逻辑
            result = func(self, user_id, *args, **kwargs)
            
            # 标记数据来源
            result["data_source"] = "REALTIME"
            
            # 缓存结果（仅非异步模式）
            if not is_async_worker:
                # 创建缓存副本（移除不需要缓存的字段）
                cache_data = result.copy()
                cache_data.pop("generated_audio", None)  # 音频数据太大，不缓存
                redis_client.set(cache_key, cache_data, ttl_seconds)
            
            return result
        
        return wrapper
    return decorator


def invalidate_user_cache(user_id: str) -> bool:
    """
    使用户缓存失效（用于数据更新后）
    
    Args:
        user_id: 用户 ID
    
    Returns:
        是否成功
    """
    cache_key = f"{CACHE_KEY_PREFIX}:{user_id}"
    return redis_client.delete(cache_key)
