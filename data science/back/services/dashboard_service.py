"""Aggregate dashboard summary for the industrial operations hub."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from config import Config
from services.history_service import HistoryService
from services.job_service import JobService
from services.ml_service import EnergyPredictor
from services.rag_service import RAGService
from services.storage_service import StorageService

logger = logging.getLogger(__name__)


class DashboardService:
    @staticmethod
    def _safe_storage_status() -> Dict[str, Any]:
        try:
            storage = StorageService()
            return {
                'key': 'storage',
                'label': 'Storage',
                'status': 'ok',
                'message': f'Bucket ready: {storage.bucket_name}',
            }
        except Exception as exc:
            return {
                'key': 'storage',
                'label': 'Storage',
                'status': 'error',
                'message': str(exc),
            }

    @staticmethod
    def _service_statuses() -> List[Dict[str, Any]]:
        model_ready = EnergyPredictor.get_model_metadata() is not None
        rag_available = bool(Config.HEAVY_SERVICE_URL) or RAGService.is_available().get('fully_available', False)
        return [
            {
                'key': 'api',
                'label': 'API',
                'status': 'ok',
                'message': 'Primary API is reachable',
            },
            DashboardService._safe_storage_status(),
            {
                'key': 'model',
                'label': 'Model',
                'status': 'ok' if model_ready else 'warning',
                'message': 'Forecast model metadata available' if model_ready else 'No production model metadata found',
            },
            {
                'key': 'rag',
                'label': 'RAG',
                'status': 'ok' if rag_available else 'warning',
                'message': 'Knowledge service ready' if rag_available else 'Knowledge service not configured',
            },
        ]

    @classmethod
    def build_summary(cls, uid: str) -> Dict[str, Any]:
        activity = HistoryService.get_recent_activity(uid, limit=8)
        jobs = JobService.list_jobs(uid, limit=12)
        recent_assets = HistoryService.get_recent_assets(uid, limit=5)
        cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_jobs_24h = JobService.count_jobs(uid, submitted_after=cutoff)
        failed_jobs = JobService.count_jobs(uid, status='failed')
        dataset_count = HistoryService.count_history_records(uid)
        analysis_count = HistoryService.count_activity(uid, activity_type='analysis', status='success')
        model_count = JobService.count_jobs(uid, job_type='ml_train', status='succeeded')

        alerts: List[Dict[str, Any]] = []
        for status in cls._service_statuses():
            if status['status'] != 'ok':
                alerts.append(
                    {
                        'severity': 'warning' if status['status'] == 'warning' else 'error',
                        'title': f"{status['label']} 状态异常",
                        'message': status['message'],
                    }
                )
        if failed_jobs:
            alerts.append(
                {
                    'severity': 'error',
                    'title': '存在失败任务',
                    'message': f'最近任务中有 {failed_jobs} 个失败项，需要检查执行日志。',
                }
            )
        if not recent_assets:
            alerts.append(
                {
                    'severity': 'info',
                    'title': '暂无近期数据资产',
                    'message': '上传数据并运行分析后，驾驶舱会显示数据资产和历史摘要。',
                }
            )

        return {
            'system_status': cls._service_statuses(),
            'kpis': {
                'dataset_count': dataset_count,
                'analysis_count': analysis_count,
                'model_count': model_count,
                'jobs_24h': recent_jobs_24h,
                'failed_jobs': failed_jobs,
            },
            'recent_jobs': jobs[:6],
            'recent_assets': recent_assets,
            'recent_history': activity,
            'alerts': alerts,
        }
