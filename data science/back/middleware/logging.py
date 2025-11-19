"""
日志中间件
记录所有 API 请求和响应
"""

import time
import logging
from flask import request, g
from functools import wraps

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_logging(app):
    """
    设置 Flask 应用的日志中间件
    
    Args:
        app: Flask 应用实例
    """
    
    @app.before_request
    def before_request():
        """请求前记录"""
        g.start_time = time.time()
        g.request_id = request.headers.get('X-Request-ID', 'unknown')
        
        logger.info(f"[{g.request_id}] {request.method} {request.path} - Start")
    
    @app.after_request
    def after_request(response):
        """请求后记录"""
        if hasattr(g, 'start_time'):
            elapsed = time.time() - g.start_time
            logger.info(
                f"[{g.request_id}] {request.method} {request.path} - "
                f"Status: {response.status_code} - "
                f"Duration: {elapsed:.3f}s"
            )
        return response
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        """全局异常处理"""
        logger.error(
            f"[{g.get('request_id', 'unknown')}] Unhandled exception: {str(e)}",
            exc_info=True
        )
        raise


def log_function_call(func):
    """
    装饰器：记录函数调用
    
    使用方法:
        @log_function_call
        def my_function():
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__} returned: {result}")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} raised exception: {str(e)}", exc_info=True)
            raise
    return wrapper
