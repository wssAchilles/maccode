"""历史记录与审计 API 路由."""

from flask import Blueprint, request
from services.firebase_service import require_auth
from services.history_service import HistoryService
from middleware.rate_limit import rate_limit
from utils.responses import error_response, success_response
import logging

logger = logging.getLogger(__name__)

history_bp = Blueprint('history', __name__, url_prefix='/api/history')


@history_bp.route('', methods=['GET'])
@require_auth
@rate_limit(max_requests=30, window_seconds=60)
def get_history():
    """
    获取用户的分析历史记录
    
    请求:
        - Method: GET
        - Headers: Authorization: Bearer <Firebase ID Token>
        - Query Parameters:
          - limit: (可选) 返回记录数量，默认 20，最大 100
    
    响应:
        {
            "success": true,
            "history": [
                {
                    "id": "record_id",
                    "filename": "data.csv",
                    "storage_url": "gs://bucket/path/to/file.csv",
                    "quality_score": 85.5,
                    "summary": {...},
                    "created_at": "2024-01-01T12:00:00Z"
                },
                ...
            ],
            "count": 10
        }
    """
    try:
        user = request.user
        uid = user.get('uid')
        
        # 获取查询参数
        limit = request.args.get('limit', default=20, type=int)
        
        # 限制最大返回数量
        if limit > 100:
            limit = 100
        elif limit < 1:
            limit = 20
        
        logger.info(f"[{uid}] 获取历史记录请求，limit={limit}")
        
        # 调用服务获取历史记录
        history = HistoryService.get_user_history(uid, limit=limit)
        
        # 转换 Firestore Timestamp 为 ISO 格式字符串
        for record in history:
            if 'created_at' in record and record['created_at']:
                # Firestore Timestamp 转换为 datetime，再转换为 ISO 字符串
                created_at = record['created_at']
                if hasattr(created_at, 'isoformat'):
                    record['created_at'] = created_at.isoformat()
                elif hasattr(created_at, 'seconds'):
                    # Firestore Timestamp 对象
                    from datetime import datetime
                    dt = datetime.fromtimestamp(created_at.seconds)
                    record['created_at'] = dt.isoformat()
        
        logger.info(f"[{uid}] 返回 {len(history)} 条历史记录")
        
        return success_response({
            'history': history,
            'count': len(history),
        })
        
    except Exception as e:
        logger.error(f"获取历史记录失败: {str(e)}", exc_info=True)
        return error_response(
            'HISTORY_FETCH_ERROR',
            f'获取历史记录失败: {str(e)}',
            status_code=500,
        )


@history_bp.route('/<record_id>', methods=['GET'])
@require_auth
@rate_limit(max_requests=50, window_seconds=60)
def get_history_detail(record_id):
    """
    获取单条历史记录的详细信息
    
    请求:
        - Method: GET
        - Headers: Authorization: Bearer <Firebase ID Token>
        - Path: /api/history/<record_id>
    
    响应:
        {
            "success": true,
            "record": {...}
        }
    """
    try:
        user = request.user
        uid = user.get('uid')
        
        logger.info(f"[{uid}] 获取历史记录详情: {record_id}")
        
        # 使用 HistoryService 获取记录
        record = HistoryService.get_history_detail(uid, record_id)
        
        if not record:
            return error_response('RECORD_NOT_FOUND', '记录不存在', status_code=404)
        
        # 转换时间戳
        if 'created_at' in record and record['created_at']:
            created_at = record['created_at']
            if hasattr(created_at, 'isoformat'):
                record['created_at'] = created_at.isoformat()
            elif hasattr(created_at, 'seconds'):
                from datetime import datetime
                dt = datetime.fromtimestamp(created_at.seconds)
                record['created_at'] = dt.isoformat()
        
        return success_response({'record': record})
        
    except Exception as e:
        logger.error(f"获取历史记录详情失败: {str(e)}", exc_info=True)
        return error_response(
            'RECORD_FETCH_ERROR',
            f'获取记录失败: {str(e)}',
            status_code=500,
        )


@history_bp.route('/<record_id>', methods=['DELETE'])
@require_auth
@rate_limit(max_requests=20, window_seconds=60)
def delete_history_record(record_id):
    """
    删除历史记录
    
    请求:
        - Method: DELETE
        - Headers: Authorization: Bearer <Firebase ID Token>
        - Path: /api/history/<record_id>
    
    响应:
        {
            "success": true,
            "message": "记录已删除"
        }
    """
    try:
        user = request.user
        uid = user.get('uid')
        
        logger.info(f"[{uid}] 删除历史记录: {record_id}")
        
        # 使用 HistoryService 删除记录
        HistoryService.delete_history_record(uid, record_id)
        
        logger.info(f"[{uid}] 历史记录已删除: {record_id}")
        
        return success_response({'message': '记录已删除'})
        
    except Exception as e:
        logger.error(f"删除历史记录失败: {str(e)}", exc_info=True)
        return error_response('DELETE_ERROR', f'删除失败: {str(e)}', status_code=500)


@history_bp.route('/activity', methods=['GET'])
@require_auth
@rate_limit(max_requests=60, window_seconds=60)
def get_activity():
    """获取用户审计活动流."""
    try:
        uid = request.user.get('uid')
        limit = request.args.get('limit', default=20, type=int) or 20
        activity_type = request.args.get('type')
        status = request.args.get('status')

        if limit > 100:
            limit = 100
        elif limit < 1:
            limit = 20

        activity = HistoryService.get_recent_activity(
            uid,
            limit=limit,
            activity_type=activity_type,
            status=status,
        )
        return success_response({
            'activity': activity,
            'count': len(activity),
        })
    except Exception as e:
        logger.error(f"获取审计活动失败: {str(e)}", exc_info=True)
        return error_response(
            'ACTIVITY_FETCH_ERROR',
            f'获取审计活动失败: {str(e)}',
            status_code=500,
        )
