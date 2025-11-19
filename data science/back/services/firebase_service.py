"""
Firebase Admin SDK 服务
用于验证用户 Token 和管理 Firebase 相关操作
"""

import firebase_admin
from firebase_admin import credentials, auth
from functools import wraps
from flask import request, jsonify


class FirebaseService:
    """Firebase 服务类"""
    
    _initialized = False
    
    @classmethod
    def initialize(cls, project_id=None):
        """
        初始化 Firebase Admin SDK
        
        Args:
            project_id: GCP 项目 ID (可选，GAE 环境会自动检测)
        """
        if cls._initialized:
            return
        
        try:
            # 在 GAE 环境中,使用默认凭证
            # 本地开发需要设置 GOOGLE_APPLICATION_CREDENTIALS 环境变量
            if project_id:
                cred = credentials.ApplicationDefault()
                firebase_admin.initialize_app(cred, {
                    'projectId': project_id,
                })
            else:
                # GAE 环境自动检测
                firebase_admin.initialize_app()
            
            cls._initialized = True
            print("✅ Firebase Admin SDK 初始化成功")
        except Exception as e:
            print(f"❌ Firebase Admin SDK 初始化失败: {e}")
            raise
    
    @staticmethod
    def verify_token(id_token):
        """
        验证 Firebase ID Token
        
        Args:
            id_token: 前端传来的 Firebase ID Token
            
        Returns:
            dict: 解码后的 Token 信息,包含 uid, email 等
            
        Raises:
            auth.InvalidIdTokenError: Token 无效
        """
        try:
            decoded_token = auth.verify_id_token(id_token)
            return decoded_token
        except auth.InvalidIdTokenError as e:
            raise ValueError(f"Invalid token: {e}")
        except Exception as e:
            raise ValueError(f"Token verification failed: {e}")
    
    @staticmethod
    def get_user(uid):
        """
        获取用户信息
        
        Args:
            uid: 用户 ID
            
        Returns:
            UserRecord: Firebase 用户记录
        """
        return auth.get_user(uid)


def require_auth(f):
    """
    装饰器: 要求请求必须携带有效的 Firebase Token
    
    使用方法:
        @app.route('/api/protected')
        @require_auth
        def protected_route():
            # request.user 包含用户信息
            user_id = request.user['uid']
            return jsonify({'message': 'Authorized'})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # OPTIONS 预检请求不需要认证
        if request.method == 'OPTIONS':
            return f(*args, **kwargs)
        
        # 从请求头获取 Token
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return jsonify({
                'error': {
                    'code': 'UNAUTHORIZED',
                    'message': 'Missing or invalid Authorization header'
                }
            }), 401
        
        # 提取 Token
        id_token = auth_header.replace('Bearer ', '')
        
        try:
            # 验证 Token
            decoded_token = FirebaseService.verify_token(id_token)
            
            # 将用户信息附加到 request 对象
            request.user = decoded_token
            
            # 调用原始函数
            return f(*args, **kwargs)
        
        except ValueError as e:
            return jsonify({
                'error': {
                    'code': 'UNAUTHORIZED',
                    'message': str(e)
                }
            }), 401
        except Exception as e:
            return jsonify({
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': 'Token verification failed'
                }
            }), 500
    
    return decorated_function
