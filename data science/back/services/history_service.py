"""History and audit persistence on Firestore."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from google.cloud import firestore
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from config import Config

logger = logging.getLogger(__name__)


class HistoryService:
    """Persist analysis history and audit activity for a user."""

    @staticmethod
    def _get_firestore_client():
        try:
            return firestore.Client(database=Config.FIRESTORE_DATABASE)
        except Exception as exc:
            logger.error('Failed to get Firestore client: %s', exc)
            raise

    @classmethod
    def _user_doc(cls, uid: str):
        return cls._get_firestore_client().collection('users').document(uid)

    @classmethod
    def _history_collection(cls, uid: str):
        return cls._user_doc(uid).collection('history')

    @classmethod
    def _activity_collection(cls, uid: str):
        return cls._user_doc(uid).collection(Config.ACTIVITY_COLLECTION)

    @staticmethod
    def _as_iso(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        if hasattr(value, 'isoformat'):
            try:
                return value.isoformat()
            except Exception:
                return value
        if isinstance(value, dict):
            return {key: HistoryService._as_iso(item) for key, item in value.items()}
        if isinstance(value, list):
            return [HistoryService._as_iso(item) for item in value]
        return value

    @staticmethod
    def _prepare_analysis_summary(analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        summary: Dict[str, Any] = {}

        if 'basic_info' in analysis_result:
            summary['basic_info'] = analysis_result['basic_info']

        if 'quality_analysis' in analysis_result:
            quality = dict(analysis_result['quality_analysis'])
            if 'outlier_detection' in quality:
                outlier_detection = {}
                for col, info in quality['outlier_detection'].items():
                    if isinstance(info, dict) and 'indices' in info:
                        outlier_detection[col] = {
                            'count': info.get('count', 0),
                            'percentage': info.get('percentage', 0.0),
                            'bounds': info.get('bounds', {}),
                        }
                    else:
                        outlier_detection[col] = info
                quality['outlier_detection'] = outlier_detection
            if 'duplicate_check' in quality and isinstance(quality['duplicate_check'], dict):
                duplicate = dict(quality['duplicate_check'])
                if 'indices' in duplicate:
                    duplicate['indices'] = duplicate['indices'][:10] if isinstance(duplicate['indices'], list) else []
                quality['duplicate_check'] = duplicate
            summary['quality_analysis'] = quality

        if 'correlations' in analysis_result:
            correlations = dict(analysis_result['correlations'])
            correlations.pop('pearson_matrix', None)
            correlations.pop('spearman_matrix', None)
            if 'correlations' in correlations and isinstance(correlations['correlations'], list):
                correlations['correlations'] = correlations['correlations'][:10]
            summary['correlations'] = correlations

        if 'statistical_tests' in analysis_result:
            stats = dict(analysis_result['statistical_tests'])
            if 'normality_tests' in stats and isinstance(stats['normality_tests'], dict):
                stats['normality_tests'] = dict(list(stats['normality_tests'].items())[:20])
            summary['statistical_tests'] = stats

        return summary

    @classmethod
    def save_analysis_record(
        cls,
        uid: str,
        filename: str,
        storage_url: str,
        analysis_result: Dict[str, Any],
    ) -> Optional[str]:
        try:
            summary = cls._prepare_analysis_summary(analysis_result)
            quality_score = None
            quality_analysis = analysis_result.get('quality_analysis')
            if isinstance(quality_analysis, dict):
                quality_score = quality_analysis.get('quality_score')

            record = {
                'record_type': 'analysis',
                'filename': filename,
                'storage_url': storage_url,
                'quality_score': quality_score,
                'summary': summary,
                'created_at': SERVER_TIMESTAMP,
            }
            doc_ref = cls._history_collection(uid).document()
            doc_ref.set(record)

            cls.add_history(
                uid=uid,
                action='analysis_completed',
                status='success',
                source='analysis',
                resource_type='history_record',
                resource_id=doc_ref.id,
                title=f'完成数据分析: {filename}',
                details={
                    'filename': filename,
                    'quality_score': quality_score,
                    'storage_url': storage_url,
                },
            )
            logger.info('Saved analysis record for user %s: %s', uid, doc_ref.id)
            return doc_ref.id
        except Exception as exc:
            logger.error('Failed to save analysis record: %s', exc)
            return None

    @classmethod
    def add_history(
        cls,
        uid: str,
        action: str,
        details: Optional[Dict[str, Any]] = None,
        status: str = 'success',
        source: str = 'system',
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        title: Optional[str] = None,
        severity: str = 'info',
    ) -> Optional[str]:
        try:
            payload = {
                'action': action,
                'status': status,
                'source': source,
                'severity': severity,
                'title': title or action,
                'details': details or {},
                'resource_type': resource_type,
                'resource_id': resource_id,
                'created_at': SERVER_TIMESTAMP,
            }
            doc_ref = cls._activity_collection(uid).document()
            doc_ref.set(payload)
            return doc_ref.id
        except Exception as exc:
            logger.warning('Failed to add history activity for user %s: %s', uid, exc)
            return None

    @classmethod
    def get_user_history(cls, uid: str, limit: int = 20) -> List[Dict[str, Any]]:
        try:
            docs = (
                cls._history_collection(uid)
                .order_by('created_at', direction=firestore.Query.DESCENDING)
                .limit(limit)
                .stream()
            )
            history = []
            for doc in docs:
                record = doc.to_dict() or {}
                record['id'] = doc.id
                history.append(record)
            return history
        except Exception as exc:
            logger.error('Failed to get user history: %s', exc)
            return []

    @classmethod
    def get_recent_assets(cls, uid: str, limit: int = 5) -> List[Dict[str, Any]]:
        assets = []
        for record in cls.get_user_history(uid, limit=limit):
            assets.append(
                {
                    'id': record.get('id'),
                    'filename': record.get('filename', 'Unknown'),
                    'quality_score': record.get('quality_score'),
                    'created_at': cls._as_iso(record.get('created_at')),
                }
            )
        return assets

    @classmethod
    def count_history_records(cls, uid: str) -> int:
        try:
            return sum(1 for _ in cls._history_collection(uid).stream())
        except Exception as exc:
            logger.error('Failed to count history records: %s', exc)
            return 0

    @classmethod
    def get_recent_activity(
        cls,
        uid: str,
        limit: int = 20,
        activity_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        try:
            normalized_statuses = None
            if status:
                status_aliases = {
                    'succeeded': {'success', 'succeeded'},
                    'success': {'success', 'succeeded'},
                    'running': {'running', 'queued'},
                    'queued': {'queued'},
                    'failed': {'failed'},
                    'cancelled': {'cancelled'},
                }
                normalized_statuses = status_aliases.get(status, {status})

            docs = (
                cls._activity_collection(uid)
                .order_by('created_at', direction=firestore.Query.DESCENDING)
                .limit(max(limit, 20))
                .stream()
            )
            activity = []
            for doc in docs:
                record = doc.to_dict() or {}
                record['id'] = doc.id
                if activity_type and record.get('source') != activity_type:
                    continue
                if normalized_statuses and record.get('status') not in normalized_statuses:
                    continue
                record['created_at'] = cls._as_iso(record.get('created_at'))
                activity.append(record)
                if len(activity) >= limit:
                    break
            return activity
        except Exception as exc:
            logger.error('Failed to get recent activity: %s', exc)
            return []

    @classmethod
    def count_activity(
        cls,
        uid: str,
        activity_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> int:
        try:
            normalized_statuses = None
            if status:
                status_aliases = {
                    'succeeded': {'success', 'succeeded'},
                    'success': {'success', 'succeeded'},
                    'running': {'running', 'queued'},
                    'queued': {'queued'},
                    'failed': {'failed'},
                    'cancelled': {'cancelled'},
                }
                normalized_statuses = status_aliases.get(status, {status})

            total = 0
            for doc in cls._activity_collection(uid).stream():
                record = doc.to_dict() or {}
                if activity_type and record.get('source') != activity_type:
                    continue
                if normalized_statuses and record.get('status') not in normalized_statuses:
                    continue
                total += 1
            return total
        except Exception as exc:
            logger.error('Failed to count activity: %s', exc)
            return 0

    @classmethod
    def get_history_detail(cls, uid: str, record_id: str) -> Optional[Dict[str, Any]]:
        try:
            doc = cls._history_collection(uid).document(record_id).get()
            if not doc.exists:
                return None
            record = doc.to_dict() or {}
            record['id'] = doc.id
            return record
        except Exception as exc:
            logger.error('Failed to get history detail: %s', exc)
            raise

    @classmethod
    def delete_history_record(cls, uid: str, record_id: str) -> bool:
        try:
            cls._history_collection(uid).document(record_id).delete()
            cls.add_history(
                uid=uid,
                action='analysis_deleted',
                status='success',
                source='history',
                resource_type='history_record',
                resource_id=record_id,
                title='删除分析记录',
            )
            return True
        except Exception as exc:
            logger.error('Failed to delete history record: %s', exc)
            raise
