"""
数据处理相关 API 路由
"""

from flask import Blueprint, jsonify, request
from services.firebase_service import require_auth
from services.storage_service import StorageService
import base64
from datetime import datetime

data_bp = Blueprint('data', __name__, url_prefix='/api/data')


@data_bp.route('/upload-url', methods=['POST'])
@require_auth
def get_upload_url():
    """
    获取文件上传的 Signed URL
    
    Request Body:
        {
            "fileName": "dataset.csv",
            "contentType": "text/csv"
        }
    
    Returns:
        JSON: 上传 URL 和目标路径
    """
    user = request.user
    data = request.get_json()
    
    # 验证输入
    if not data or 'fileName' not in data:
        return jsonify({
            'error': {
                'code': 'BAD_REQUEST',
                'message': 'Missing fileName'
            }
        }), 400
    
    try:
        file_name = data['fileName']
        content_type = data.get('contentType', 'application/octet-stream')
        
        # 生成唯一文件路径
        user_id = user['uid']
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        destination_path = f"uploads/{user_id}/{timestamp}_{file_name}"
        
        # 获取 Signed URL
        storage = StorageService()
        upload_url = storage.generate_upload_signed_url(destination_path, content_type)
        
        return jsonify({
            'success': True,
            'uploadUrl': upload_url,
            'storagePath': destination_path,
            'fileName': file_name,
            'expiresIn': 900  # 15 分钟
        }), 200
    
    except Exception as e:
        return jsonify({
            'error': {
                'code': 'Generate_URL_FAILED',
                'message': str(e)
            }
        }), 500


@data_bp.route('/list', methods=['GET'])
@require_auth
def list_user_files():
    """
    列出用户上传的所有文件
    
    Returns:
        JSON: 文件列表
    """
    user = request.user
    user_id = user['uid']
    
    try:
        storage = StorageService()
        files = storage.list_files(prefix=f"uploads/{user_id}/")
        
        return jsonify({
            'success': True,
            'files': files,
            'count': len(files)
        }), 200
    
    except Exception as e:
        return jsonify({
            'error': {
                'code': 'LIST_FAILED',
                'message': str(e)
            }
        }), 500


@data_bp.route('/download/<path:file_path>', methods=['GET'])
@require_auth
def download_file(file_path):
    """
    生成文件下载链接
    
    Args:
        file_path: 文件路径
    
    Returns:
        JSON: 签名 URL
    """
    user = request.user
    user_id = user['uid']
    
    # 验证用户只能访问自己的文件
    if not file_path.startswith(f"uploads/{user_id}/"):
        return jsonify({
            'error': {
                'code': 'FORBIDDEN',
                'message': 'Access denied'
            }
        }), 403
    
    try:
        storage = StorageService()
        signed_url = storage.get_signed_url(file_path, expiration_minutes=30)
        
        return jsonify({
            'success': True,
            'downloadUrl': signed_url,
            'expiresIn': 1800  # 30 分钟
        }), 200
    
    except Exception as e:
        return jsonify({
            'error': {
                'code': 'DOWNLOAD_FAILED',
                'message': str(e)
            }
        }), 500
