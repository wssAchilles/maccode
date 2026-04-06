"""Dashboard aggregation API."""

from __future__ import annotations

import logging

from flask import Blueprint, request

from middleware.rate_limit import rate_limit
from services.dashboard_service import DashboardService
from services.firebase_service import require_auth
from services.runtime_cache_service import RuntimeCacheService
from utils.responses import error_response, success_response

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')


@dashboard_bp.route('/summary', methods=['GET', 'OPTIONS'])
@rate_limit(max_requests=30, window_seconds=60)
@require_auth
def get_dashboard_summary():
    if request.method == 'OPTIONS':
        return success_response({'status': 'ok'})

    try:
        uid = request.user.get('uid')
        payload = RuntimeCacheService.get_or_set(
            f'dashboard:summary:{uid}',
            lambda: DashboardService.build_summary(uid),
            ttl_s=20,
        )
        return success_response(payload)
    except Exception as exc:
        logger.error('Failed to build dashboard summary: %s', exc, exc_info=True)
        return error_response('DASHBOARD_SUMMARY_ERROR', f'获取驾驶舱摘要失败: {exc}', status_code=500)


@dashboard_bp.route('/assets', methods=['GET', 'OPTIONS'])
@rate_limit(max_requests=30, window_seconds=60)
@require_auth
def get_dashboard_assets():
    if request.method == 'OPTIONS':
        return success_response({'status': 'ok'})

    try:
        uid = request.user.get('uid')
        limit = int(request.args.get('limit', 6))
        payload = RuntimeCacheService.get_or_set(
            f'dashboard:assets:{uid}:{limit}',
            lambda: DashboardService.build_asset_summary(uid, limit=limit),
            ttl_s=30,
        )
        return success_response(payload)
    except Exception as exc:
        logger.error('Failed to build asset summary: %s', exc, exc_info=True)
        return error_response('DASHBOARD_ASSET_SUMMARY_ERROR', f'获取资产摘要失败: {exc}', status_code=500)
