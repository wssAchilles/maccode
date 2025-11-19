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
    """简单的内存限流器"""
    
    def __init__(self):
        self.requests = defaultdict(list)
        self.lock = Lock()
    
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
            
            # 清理过期请求记录
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
