"""
认证相关 API 路由
"""

from flask import Blueprint, jsonify, request
from services.firebase_service import require_auth

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/verify', methods=['POST'])
@require_auth
def verify_token():
    """
    验证用户 Token
    前端可以调用此接口验证 Token 是否有效
    
    Returns:
        JSON: 用户信息
    """
    user = request.user
    
    return jsonify({
        'success': True,
        'user': {
            'uid': user.get('uid'),
            'email': user.get('email'),
            'name': user.get('name'),
            'picture': user.get('picture'),
        }
    }), 200


@auth_bp.route('/profile', methods=['GET'])
@require_auth
def get_profile():
    """
    获取用户资料
    
    Returns:
        JSON: 用户详细信息
    """
    user = request.user
    
    return jsonify({
        'success': True,
        'profile': {
            'uid': user.get('uid'),
            'email': user.get('email'),
            'emailVerified': user.get('email_verified', False),
            'displayName': user.get('name'),
            'photoURL': user.get('picture'),
            'createdAt': user.get('auth_time'),
        }
    }), 200
