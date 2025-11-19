"""
自定义异常类
统一的错误处理
"""


class APIException(Exception):
    """API 基础异常类"""
    
    def __init__(self, message, status_code=500, error_code=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or 'INTERNAL_ERROR'
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'error': {
                'code': self.error_code,
                'message': self.message
            }
        }


class AuthenticationError(APIException):
    """认证错误"""
    
    def __init__(self, message="Authentication failed"):
        super().__init__(message, status_code=401, error_code='AUTHENTICATION_ERROR')


class AuthorizationError(APIException):
    """授权错误"""
    
    def __init__(self, message="Permission denied"):
        super().__init__(message, status_code=403, error_code='AUTHORIZATION_ERROR')


class ValidationError(APIException):
    """数据验证错误"""
    
    def __init__(self, message="Validation failed"):
        super().__init__(message, status_code=400, error_code='VALIDATION_ERROR')


class ResourceNotFoundError(APIException):
    """资源不存在错误"""
    
    def __init__(self, resource_type="Resource", resource_id=None):
        message = f"{resource_type} not found"
        if resource_id:
            message += f": {resource_id}"
        super().__init__(message, status_code=404, error_code='RESOURCE_NOT_FOUND')


class StorageError(APIException):
    """存储服务错误"""
    
    def __init__(self, message="Storage operation failed"):
        super().__init__(message, status_code=500, error_code='STORAGE_ERROR')


class ModelError(APIException):
    """机器学习模型错误"""
    
    def __init__(self, message="Model operation failed"):
        super().__init__(message, status_code=500, error_code='MODEL_ERROR')


class DataProcessingError(APIException):
    """数据处理错误"""
    
    def __init__(self, message="Data processing failed"):
        super().__init__(message, status_code=500, error_code='DATA_PROCESSING_ERROR')


def register_error_handlers(app):
    """
    注册全局错误处理器到 Flask 应用
    
    Args:
        app: Flask 应用实例
    """
    from flask import jsonify
    
    @app.errorhandler(APIException)
    def handle_api_exception(error):
        """处理自定义 API 异常"""
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response
    
    @app.errorhandler(404)
    def handle_404(error):
        """处理 404 错误"""
        return jsonify({
            'error': {
                'code': 'NOT_FOUND',
                'message': 'Resource not found'
            }
        }), 404
    
    @app.errorhandler(500)
    def handle_500(error):
        """处理 500 错误"""
        return jsonify({
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Internal server error'
            }
        }), 500
