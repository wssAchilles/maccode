"""
RAG (Retrieval-Augmented Generation) API 路由
处理文档上传、索引构建和智能问答请求
"""

from flask import Blueprint, jsonify, request
from services.firebase_service import require_auth
from services.rag_service import RAGService
from services.storage_service import StorageService
from services.history_service import HistoryService
from utils.exceptions import ValidationError
from middleware.rate_limit import rate_limit
import logging
import os
import shutil
import tempfile

logger = logging.getLogger(__name__)

rag_bp = Blueprint('rag', __name__, url_prefix='/api/rag')

@rag_bp.route('/status', methods=['GET', 'OPTIONS'])
@rate_limit(max_requests=60, window_seconds=60)
@require_auth
def get_status():
    """
    获取 RAG 系统状态
    
    响应:
        {
            "success": true,
            "available": true,
            "stats": {
                "count": 120,
                "collections": ["default"],
                "persist_directory": "..."
            }
        }
    """
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    try:
        user = request.user
        uid = user.get('uid')
        collection_name = (
            request.args.get('collection_name')
            or request.args.get('collection')
            or f"user_{uid}"
        )

        service = RAGService(collection_name=collection_name)
        available = service.is_available()

        stats = {}
        if available.get('available'):
            stats = service.get_stats()
            
        return jsonify({
            'success': True,
            'available': available.get('available', False),
            'collection': collection_name,
            'backend': stats.get('backend'),
            'dependencies': available,
            'stats': stats
        }), 200
        
    except Exception as e:
        logger.error(f"获取 RAG 状态失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'SERVER_ERROR',
            'message': f'服务器错误: {str(e)}'
        }), 500

@rag_bp.route('/ingest', methods=['POST', 'OPTIONS'])
@rate_limit(max_requests=10, window_seconds=300)
@require_auth
def ingest_documents():
    """
    接收文档并构建向量索引
    
    请求:
        - storage_path: GCS 中的文件或目录路径
        - collection_name: (可选) 集合名称
        - reset: (可选) 是否重置索引
    """
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200

    try:
        user = request.user
        uid = user.get('uid')
        data = request.get_json() or {}
        
        storage_path = data.get('storage_path')
        collection_name = data.get('collection_name', f"user_{uid}")
        reset = data.get('reset', False)
        
        if not storage_path:
            raise ValidationError('缺少参数: storage_path')
            
        logger.info(f"[{uid}] 开始 RAG 索引构建: {storage_path}")
        
        service = RAGService(collection_name=collection_name)
        availability = service.is_available()
        if not availability.get('available'):
            raise ValidationError('RAG 服务当前不可用')

        # 下载文件到临时目录
        storage = StorageService()
        with tempfile.TemporaryDirectory() as temp_dir:
            local_path = os.path.join(temp_dir, 'docs')
            os.makedirs(local_path, exist_ok=True)
            
            # 简单处理：如果是单个文件
            if not storage_path.endswith('/'):
                file_bytes = storage.download_file(storage_path)
                fname = os.path.basename(storage_path)
                with open(os.path.join(local_path, fname), 'wb') as f:
                    f.write(file_bytes)
            else:
                # TODO: 支持目录下载 (StorageService 需要扩展 list_files + download)
                # 暂时只支持单个文件或假设 storage_path 是前缀
                files = storage.list_files(storage_path)
                for fpath in files:
                    if fpath.endswith('/'): continue
                    file_bytes = storage.download_file(fpath)
                    fname = os.path.basename(fpath)
                    with open(os.path.join(local_path, fname), 'wb') as f:
                        f.write(file_bytes)
            
            if reset:
                service.reset_collection()
            documents = service.load_documents(local_path)
            count = service.create_embeddings(documents)
            stats = service.get_stats()
            
        return jsonify({
            'success': True,
            'message': f'成功索引 {count} 个文档片段',
            'count': count,
            'collection': collection_name,
            'stats': stats,
        }), 200

    except ValidationError as e:
        return jsonify({'success': False, 'error': 'VALIDATION_ERROR', 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"RAG 索引构建失败: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': 'SERVER_ERROR', 'message': str(e)}), 500

@rag_bp.route('/ask', methods=['POST', 'OPTIONS'])
@rate_limit(max_requests=30, window_seconds=60)
@require_auth
def query_rag():
    """
    RAG 问答
    
    请求:
        - query: 问题文本
        - collection_name: (可选)
        - n_results: (可选) 返回文档片段数
    """
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200

    try:
        user = request.user
        uid = user.get('uid')
        data = request.get_json() or {}
        
        query_text = data.get('query')
        collection_name = data.get('collection_name', f"user_{uid}")
        n_results = data.get('n_results', 3)
        
        if not query_text:
            raise ValidationError('缺少参数: query')
            
        service = RAGService(collection_name=collection_name)
        availability = service.is_available()
        if not availability.get('available'):
            raise ValidationError('RAG 服务不可用')
        try:
            n_results = max(1, int(n_results))
        except (TypeError, ValueError):
            raise ValidationError('n_results 必须为正整数')
            
        # 执行查询
        answer_result = service.answer_question(query_text, top_k=n_results)
        
        # 记录历史
        try:
             HistoryService().add_history(
                uid=uid,
                action='rag_query',
                details={'query': query_text, 'answer_snippet': answer_result['answer'][:50]},
                status='success'
            )
        except:
            pass

        return jsonify({
            'success': True,
            'collection': collection_name,
            'result': answer_result
        }), 200

    except ValidationError as e:
        return jsonify({'success': False, 'error': 'VALIDATION_ERROR', 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"RAG 查询失败: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': 'SERVER_ERROR', 'message': str(e)}), 500
