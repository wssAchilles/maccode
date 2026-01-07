"""
API 限流中间件
防止 API 滥用
"""

from flask import request, jsonify
from functools import wraps
import time
from collections import defaultdict
from threading import Lock


class RateLimiter:
    """简单的内存限流器（带自动清理）"""
    
    def __init__(self, cleanup_interval: int = 300):
        """
        初始化限流器
        
        Args:
            cleanup_interval: 清理间隔（秒），默认5分钟
        """
        self.requests = defaultdict(list)
        self.lock = Lock()
        self.cleanup_interval = cleanup_interval
        self.last_cleanup = time.time()
    
    def _cleanup_stale_keys(self, window_seconds: int = 60):
        """
        清理过期的键（防止内存泄漏）
        
        Args:
            window_seconds: 时间窗口（秒）
        """
        now = time.time()
        
        # 只在间隔时间后执行清理
        if now - self.last_cleanup < self.cleanup_interval:
            return
        
        self.last_cleanup = now
        window_start = now - window_seconds
        
        # 找出需要删除的键
        keys_to_delete = []
        for key, timestamps in self.requests.items():
            # 如果所有请求都已过期，标记删除
            if not timestamps or all(t <= window_start for t in timestamps):
                keys_to_delete.append(key)
        
        # 删除过期键
        for key in keys_to_delete:
            del self.requests[key]
        
        if keys_to_delete:
            print(f"🧹 RateLimiter 清理了 {len(keys_to_delete)} 个过期键")
    
    def is_allowed(self, key, max_requests=100, window_seconds=60):
        """
        检查是否允许请求
        
        Args:
            key: 限流键（通常是用户ID或IP）
            max_requests: 时间窗口内最大请求数
            window_seconds: 时间窗口（秒）
            
        Returns:
            bool: 是否允许请求
        """
        with self.lock:
            now = time.time()
            window_start = now - window_seconds
            
            # 定期清理过期键（防止内存泄漏）
            self._cleanup_stale_keys(window_seconds)
            
            # 清理当前键的过期请求记录
            self.requests[key] = [
                req_time for req_time in self.requests[key]
                if req_time > window_start
            ]
            
            # 检查是否超过限制
            if len(self.requests[key]) >= max_requests:
                return False
            
            # 记录当前请求
            self.requests[key].append(now)
            return True
    
    def get_stats(self):
        """
        获取限流器统计信息（用于监控）
        
        Returns:
            dict: 统计信息
        """
        with self.lock:
            return {
                'active_keys': len(self.requests),
                'total_records': sum(len(v) for v in self.requests.values()),
                'last_cleanup': self.last_cleanup
            }


# 全局限流器实例
_rate_limiter = RateLimiter()


def rate_limit(max_requests=100, window_seconds=60):
    """
    限流装饰器
    
    Args:
        max_requests: 时间窗口内最大请求数
        window_seconds: 时间窗口（秒）
    
    使用方法:
        @app.route('/api/endpoint')
        @rate_limit(max_requests=10, window_seconds=60)
        def my_endpoint():
            return jsonify({'status': 'ok'})
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 使用用户 ID 或 IP 作为限流键
            from flask import current_app
            if current_app.config.get('TESTING'):
                return f(*args, **kwargs)

            if hasattr(request, 'user') and request.user:
                key = f"user:{request.user.get('uid')}"
            else:
                key = f"ip:{request.remote_addr}"
            
            if not _rate_limiter.is_allowed(key, max_requests, window_seconds):
                return jsonify({
                    'error': {
                        'code': 'RATE_LIMIT_EXCEEDED',
                        'message': f'Too many requests. Limit: {max_requests} per {window_seconds}s'
                    }
                }), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
