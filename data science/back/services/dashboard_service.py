"""Aggregate dashboard summary for the industrial operations hub."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from config import Config
from services.history_service import HistoryService
from services.job_service import JobService
from services.ml_service import EnergyPredictor
from services.rag_service import RAGService
from services.storage_service import StorageService

logger = logging.getLogger(__name__)


class DashboardService:
    CHAIN_OPERATIONS_CONFIG = {
        'dataset': {
            'owner_label': '数据工作台值班',
            'sla_minutes': 30,
            'escalation_label': '升级到数据治理负责人',
        },
        'model': {
            'owner_label': '模型训练值班',
            'sla_minutes': 45,
            'escalation_label': '升级到 ML 负责人',
        },
        'knowledge': {
            'owner_label': '知识库值班',
            'sla_minutes': 45,
            'escalation_label': '升级到 AI 知识平台主管',
        },
        'optimization': {
            'owner_label': '优化求解值班',
            'sla_minutes': 20,
            'escalation_label': '升级到能源调度负责人',
        },
    }

    FAILURE_CHAIN_CONFIG = {
        'analysis': {
            'key': 'dataset',
            'label': '数据分析失败链路',
            'action_label': '打开数据分析',
            'recommended_action': '检查上传文件、归档路径和分析输入字段是否完整。',
        },
        'ml_train': {
            'key': 'model',
            'label': '模型训练失败链路',
            'action_label': '打开 AI Lab',
            'recommended_action': '优先检查训练数据路径、目标列和模型参数配置。',
        },
        'rag_ingest': {
            'key': 'knowledge',
            'label': '知识构建失败链路',
            'action_label': '打开 AI Lab',
            'recommended_action': '优先检查文档路径、集合名和重建模式。',
        },
        'optimization': {
            'key': 'optimization',
            'label': '优化求解失败链路',
            'action_label': '打开能源优化',
            'recommended_action': '优先检查目标日期、电池参数和求解器输入约束。',
        },
    }

    RUNBOOK_BASE = {
        'dataset': {
            'label': '数据资产',
            'action': '打开数据分析',
            'healthy_steps': (
                '复核最近归档资产的 schema、质量评分和 storage path 是否仍可复用。',
                '确认基线资产可用于漂移检测，并保留训练与知识库交接摘要。',
                '如有新的上传或审计活动，优先从数据工作台继续治理。',
            ),
        },
        'model': {
            'label': '模型资产',
            'action': '打开 AI Lab',
            'healthy_steps': (
                '确认最新模型版本的目标列、训练数据路径和产物路径仍然有效。',
                '复查最近训练指标与版本血缘，避免工作台继续使用陈旧模型。',
                '如有新的数据资产，评估是否需要重训或回填到下游工作台。',
            ),
        },
        'knowledge': {
            'label': '知识快照',
            'action': '打开 AI Lab',
            'healthy_steps': (
                '确认最新知识快照的 collection、来源路径和构建模式仍然可追溯。',
                '抽样验证问答引用来源，避免知识库快照与当前资产脱节。',
                '如有新文档或数据资产，评估是否需要增量或重建知识库。',
            ),
        },
        'optimization': {
            'label': '优化快照',
            'action': '打开能源优化',
            'healthy_steps': (
                '复核最近优化快照的目标日期、电池参数和节省摘要是否符合当前场景。',
                '确认结果快照已经归档，便于回放、复盘和导出协作摘要。',
                '如输入约束或模型版本变化，优先重新运行后台优化任务。',
            ),
        },
    }

    DUTY_ACTION_DEFAULTS = {
        'dataset': {
            'label': '上传并分析数据',
            'tone': 'primary',
            'workspace_target': 'data_governance',
            'card_target': 'current_asset',
            'incident_target': 'asset',
            'workspace_brief': '资产治理板 · 复核最新数据资产、漂移报告与治理结论。',
        },
        'model': {
            'label': '开始模型训练',
            'tone': 'tonal',
            'workspace_target': 'ai_runtime',
            'card_target': 'runtime_product',
            'incident_target': 'runtime',
            'workspace_brief': 'AI 运行控制区 · 跟进训练任务、产物版本和最新模型资产。',
        },
        'knowledge': {
            'label': '构建知识库',
            'tone': 'outline',
            'workspace_target': 'ai_runtime',
            'card_target': 'runtime_product',
            'incident_target': 'runtime',
            'workspace_brief': 'AI 运行控制区 · 跟进知识构建任务、集合快照和问答治理。',
        },
        'optimization': {
            'label': '运行能源优化',
            'tone': 'tonal',
            'workspace_target': 'optimization_operations',
            'card_target': 'solver_health',
            'incident_target': 'asset',
            'workspace_brief': '优化运维板 · 复核求解器健康、结果快照与最近优化资产。',
        },
    }

    @staticmethod
    def _governance_item(
        *,
        key: str,
        label: str,
        asset_count: int,
        failed_jobs: int,
        latest_version: str = '--',
        latest_label: str = '--',
        lineage_summary: str = '--',
        failure_summary: str = '--',
        missing_message: str,
        recovery_message: str,
        healthy_message: str,
        action_label: str,
        owner_label: str,
        sla_minutes: int,
        escalation_label: str,
    ) -> Dict[str, Any]:
        if asset_count == 0:
            risk_level = 'action'
            recommended_action = missing_message
        elif failed_jobs > 0:
            risk_level = 'watch'
            recommended_action = recovery_message.format(failed_jobs=failed_jobs)
        else:
            risk_level = 'healthy'
            recommended_action = healthy_message

        workspace_target = {
            'dataset': 'data_governance',
            'model': 'ai_assets',
            'knowledge': 'ai_assets',
            'optimization': 'optimization_registry',
        }.get(key, 'workspace')

        return {
            'key': key,
            'label': label,
            'risk_level': risk_level,
            'asset_count': asset_count,
            'failed_jobs': failed_jobs,
            'latest_version': latest_version,
            'latest_label': latest_label,
            'lineage_summary': lineage_summary,
            'failure_summary': failure_summary,
            'recommended_action': recommended_action,
            'action_label': action_label,
            'workspace_target': workspace_target,
            'workspace_target_label': DashboardService._workspace_target_label(workspace_target),
            'workspace_brief': DashboardService._compact_text(
                f'{DashboardService._workspace_target_label(workspace_target)} · {recommended_action}',
                max_length=88,
            ),
            'owner_label': owner_label,
            'sla_minutes': sla_minutes,
            'escalation_label': escalation_label,
        }

    @classmethod
    def _failure_chain_item(cls, job_type: str, job: Dict[str, Any]) -> Dict[str, Any]:
        config = cls.FAILURE_CHAIN_CONFIG[job_type]
        error = job.get('error') or {}
        events = job.get('events') or []
        latest_event = events[-1] if isinstance(events, list) and events else {}
        completed_at = job.get('completed_at') or job.get('submitted_at')
        if job_type == 'analysis':
            context_label = (job.get('input') or {}).get('filename') or (job.get('input') or {}).get('storage_path') or '--'
        elif job_type == 'ml_train':
            input_payload = job.get('input') or {}
            context_label = f"{input_payload.get('model_type', '--')} / {input_payload.get('target_column', '--')}"
        elif job_type == 'rag_ingest':
            input_payload = job.get('input') or {}
            context_label = input_payload.get('collection_name') or input_payload.get('storage_path') or '--'
        else:
            input_payload = job.get('input') or {}
            context_label = input_payload.get('target_date') or '--'

        workspace_target = {
            'analysis': 'data_job_center',
            'ml_train': 'ai_runtime',
            'rag_ingest': 'ai_runtime',
            'optimization': 'optimization_job_center',
        }.get(job_type, 'workspace')

        return {
            'key': config['key'],
            'job_type': job_type,
            'label': config['label'],
            'job_id': job.get('job_id'),
            'context_label': str(context_label),
            'latest_phase': (latest_event.get('phase') or 'failed'),
            'status_message': job.get('status_message') or (error.get('message') or '任务失败'),
            'error_code': error.get('code') or 'JOB_FAILED',
            'error_message': error.get('message') or '任务失败',
            'source_summary': cls._source_summary(job_type, job),
            'lineage_summary': cls._lineage_summary(job_type, job),
            'attempt_count': job.get('attempt_count') or 0,
            'max_attempts': job.get('max_attempts') or 1,
            'submitted_at': job.get('submitted_at'),
            'completed_at': job.get('completed_at'),
            'latest_version': cls._version_label(completed_at),
            'recommended_action': config['recommended_action'],
            'action_label': config['action_label'],
            'workspace_target': workspace_target,
            'workspace_target_label': cls._workspace_target_label(workspace_target),
            'workspace_brief': cls._compact_text(
                f"{cls._workspace_target_label(workspace_target)} · {latest_event.get('phase') or 'failed'} · {error.get('message') or '任务失败'}",
                max_length=88,
            ),
            'owner_label': cls.CHAIN_OPERATIONS_CONFIG[config['key']]['owner_label'],
            'sla_minutes': cls.CHAIN_OPERATIONS_CONFIG[config['key']]['sla_minutes'],
            'escalation_label': cls.CHAIN_OPERATIONS_CONFIG[config['key']]['escalation_label'],
        }

    @staticmethod
    def _activity_key(activity: Dict[str, Any]) -> str:
        source = str(activity.get('source') or '').lower()
        action = str(activity.get('action') or '').lower()
        if source in {'analysis', 'history'}:
            return 'dataset'
        if source == 'ml_train' or 'train' in action:
            return 'model'
        if source in {'rag', 'rag_ingest'} or 'rag' in action:
            return 'knowledge'
        if source == 'optimization' or 'optimization' in action:
            return 'optimization'
        return 'dataset'

    @staticmethod
    def _job_key(job: Dict[str, Any]) -> str:
        job_type = str(job.get('type') or '').lower()
        if job_type == 'analysis':
            return 'dataset'
        if job_type == 'ml_train':
            return 'model'
        if job_type == 'rag_ingest':
            return 'knowledge'
        if job_type == 'optimization':
            return 'optimization'
        return 'dataset'

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

    @staticmethod
    def _version_label(value: Any) -> str:
        if isinstance(value, datetime):
            return value.strftime('%m%d-%H%M')
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value).strftime('%m%d-%H%M')
            except Exception:
                return value[:8]
        return '--'

    @staticmethod
    def _compact_text(value: Any, fallback: str = '--', max_length: int = 54) -> str:
        text = str(value).strip() if value is not None else ''
        if not text:
            return fallback
        if len(text) <= max_length:
            return text
        return f"{text[: max_length - 1]}…"

    @staticmethod
    def _as_datetime(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            if value.tzinfo is not None:
                return value.astimezone(timezone.utc).replace(tzinfo=None)
            return value
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return None
            try:
                parsed = datetime.fromisoformat(raw.replace('Z', '+00:00'))
                if parsed.tzinfo is not None:
                    return parsed.astimezone(timezone.utc).replace(tzinfo=None)
                return parsed
            except Exception:
                return None
        return None

    @classmethod
    def _source_summary(cls, job_type: str, job: Dict[str, Any]) -> str:
        input_payload = job.get('input') or {}
        result_payload = job.get('result') or {}
        if job_type == 'analysis':
            return cls._compact_text(
                input_payload.get('filename') or input_payload.get('storage_path'),
            )
        if job_type == 'ml_train':
            source = cls._compact_text(input_payload.get('storage_path'))
            target = cls._compact_text(input_payload.get('target_column'))
            return f'{source} -> {target}'
        if job_type == 'rag_ingest':
            source = cls._compact_text(input_payload.get('storage_path'))
            collection = cls._compact_text(
                result_payload.get('collection') or input_payload.get('collection_name'),
            )
            return f'{source} -> {collection}'
        if job_type == 'optimization':
            target_date = cls._compact_text(input_payload.get('target_date'))
            return f'{target_date} -> battery config'
        return '--'

    @classmethod
    def _lineage_summary(cls, job_type: str, job: Dict[str, Any]) -> str:
        input_payload = job.get('input') or {}
        result_payload = job.get('result') or {}
        if job_type == 'analysis':
            filename = cls._compact_text(input_payload.get('filename'))
            storage_path = cls._compact_text(
                result_payload.get('storage_path') or input_payload.get('storage_path'),
            )
            return f'{filename} -> {storage_path}'
        if job_type == 'ml_train':
            storage_path = cls._compact_text(input_payload.get('storage_path'))
            target = cls._compact_text(input_payload.get('target_column'))
            model_type = cls._compact_text(
                result_payload.get('model_type') or input_payload.get('model_type'),
            )
            return f'{storage_path} -> {target} -> {model_type}'
        if job_type == 'rag_ingest':
            storage_path = cls._compact_text(input_payload.get('storage_path'))
            collection = cls._compact_text(
                result_payload.get('collection') or input_payload.get('collection_name'),
            )
            mode = 'reset' if input_payload.get('reset') else 'incremental'
            return f'{storage_path} -> {collection} -> {mode}'
        if job_type == 'optimization':
            target_date = cls._compact_text(input_payload.get('target_date'))
            capacity = cls._compact_text(input_payload.get('battery_capacity'))
            power = cls._compact_text(input_payload.get('battery_power'))
            return f'{target_date} -> {capacity}kWh/{power}kW'
        return '--'

    @classmethod
    def _dataset_lineage(cls, dataset: Dict[str, Any]) -> str:
        filename = cls._compact_text(dataset.get('filename'))
        rows = dataset.get('rows') if dataset.get('rows') is not None else '--'
        columns = dataset.get('columns') if dataset.get('columns') is not None else '--'
        return f'{filename} -> rows={rows} / cols={columns}'

    @classmethod
    def _model_lineage(cls, model: Dict[str, Any]) -> str:
        source = cls._compact_text(model.get('storage_path'))
        target = cls._compact_text(model.get('target_column'))
        model_type = cls._compact_text(model.get('model_type'))
        return f'{source} -> {target} -> {model_type}'

    @classmethod
    def _knowledge_lineage(cls, knowledge: Dict[str, Any]) -> str:
        source = cls._compact_text(knowledge.get('storage_path'))
        collection = cls._compact_text(knowledge.get('collection'))
        mode = 'reset' if knowledge.get('reset') else 'incremental'
        return f'{source} -> {collection} -> {mode}'

    @classmethod
    def _optimization_lineage(cls, optimization: Dict[str, Any]) -> str:
        target_date = cls._compact_text(optimization.get('target_date'))
        capacity = cls._compact_text(optimization.get('battery_capacity'))
        power = cls._compact_text(optimization.get('battery_power'))
        return f'{target_date} -> {capacity}kWh/{power}kW'

    @classmethod
    def _chain_summary(
        cls,
        *,
        key: str,
        label: str,
        governance: Dict[str, Any],
        failure: Dict[str, Any] | None,
        activity: Dict[str, Any] | None,
        latest_job: Dict[str, Any] | None,
        timeline: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if failure:
            status = 'incident'
        elif latest_job and latest_job.get('status') in {'queued', 'running'}:
            status = 'active'
        else:
            status = governance.get('risk_level') or 'healthy'
        priority_score = cls._priority_score(
            status=status,
            governance=governance,
            failure=failure,
            latest_job=latest_job,
        )
        focus_label, focus_detail = cls._focus_summary(
            status=status,
            governance=governance,
            failure=failure,
            latest_job=latest_job,
        )
        focus_target = cls._focus_target(
            key=key,
            status=status,
            failure=failure,
            latest_job=latest_job,
        )
        section_target = cls._section_target(key=key, focus_target=focus_target)
        workspace_target = cls._workspace_target(
            key=key,
            focus_target=focus_target,
            section_target=section_target,
        )
        runbook = cls._runbook_summary(
            key=key,
            status=status,
            governance=governance,
            failure=failure,
            latest_job=latest_job,
        )
        escalation = cls._escalation_summary(
            status=status,
            governance=governance,
            failure=failure,
            latest_job=latest_job,
            activity=activity,
        )
        narrative_target = cls._narrative_target(
            focus_target=focus_target,
            is_overdue=bool(escalation.get('is_overdue')),
            status=status,
            failure=failure,
        )
        incident_target = cls._incident_target(
            focus_target=focus_target,
            is_overdue=bool(escalation.get('is_overdue')),
            status=status,
            failure=failure,
            latest_job=latest_job,
            activity=activity,
        )
        disposition_target = cls._disposition_target(
            focus_target=focus_target,
            is_overdue=bool(escalation.get('is_overdue')),
            status=status,
            failure=failure,
        )
        latest_job_event = None
        if latest_job:
            events = latest_job.get('events') or []
            if isinstance(events, list) and events:
                latest_job_event = events[-1]
        return {
            'key': key,
            'label': label,
            'status': status,
            'status_label': cls._status_label(status),
            'priority_score': priority_score,
            'owner_label': governance.get('owner_label') or '--',
            'sla_minutes': governance.get('sla_minutes') or 0,
            'escalation_label': governance.get('escalation_label') or '--',
            'sla_deadline_at': escalation.get('sla_deadline_at'),
            'elapsed_minutes': escalation.get('elapsed_minutes') or 0,
            'overdue_minutes': escalation.get('overdue_minutes') or 0,
            'is_overdue': escalation.get('is_overdue') or False,
            'escalation_tier': escalation.get('escalation_tier') or 0,
            'escalation_state_label': escalation.get('escalation_state_label') or '--',
            'latest_version': governance.get('latest_version') or '--',
            'latest_label': governance.get('latest_label') or '--',
            'lineage_summary': governance.get('lineage_summary') or '--',
            'failure_summary': governance.get('failure_summary') or '--',
            'focus_label': focus_label,
            'focus_detail': focus_detail,
            'focus_target': focus_target,
            'focus_target_label': cls._focus_target_label(focus_target),
            'section_target': section_target,
            'section_target_label': cls._section_target_label(section_target),
            'workspace_target': workspace_target,
            'workspace_target_label': cls._workspace_target_label(workspace_target),
            'workspace_brief': cls._workspace_brief(
                workspace_target=workspace_target,
                section_target=section_target,
                incident_target=incident_target,
                focus_target=focus_target,
                latest_job=latest_job,
                governance=governance,
                failure=failure,
            ),
            'incident_target': incident_target,
            'incident_target_label': cls._incident_target_label(incident_target),
            'incident_brief': cls._incident_brief(
                incident_target=incident_target,
                focus_target=focus_target,
                section_target=section_target,
                focus_detail=focus_detail,
                escalation=escalation,
                latest_job=latest_job,
                activity=activity,
                governance=governance,
                failure=failure,
            ),
            'narrative_target': narrative_target,
            'narrative_target_label': cls._narrative_target_label(narrative_target),
            'disposition_target': disposition_target,
            'disposition_target_label': cls._disposition_target_label(disposition_target),
            'runbook_title': runbook['title'],
            'runbook_steps': runbook['steps'],
            'activity_title': (activity or {}).get('title') or '--',
            'activity_status': (activity or {}).get('status') or '--',
            'activity_source': (activity or {}).get('source') or '--',
            'activity_at': (activity or {}).get('created_at'),
            'failure_job_id': (failure or {}).get('job_id'),
            'failure_phase': (failure or {}).get('latest_phase') or '--',
            'failure_source': (failure or {}).get('source_summary') or '--',
            'job_status': (latest_job or {}).get('status') or '--',
            'job_progress': (latest_job or {}).get('progress') or 0,
            'job_phase': (latest_job_event or {}).get('phase') or '--',
            'action_label': (failure or {}).get('action_label') or governance.get('action_label') or '打开工作台',
            'timeline': timeline,
        }

    @classmethod
    def _runbook_summary(
        cls,
        *,
        key: str,
        status: str,
        governance: Dict[str, Any],
        failure: Dict[str, Any] | None,
        latest_job: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        base = cls.RUNBOOK_BASE[key]
        action_label = governance.get('action_label') or base['action']

        if failure:
            latest_phase = cls._compact_text(failure.get('latest_phase') or 'failed')
            source_summary = cls._compact_text(
                failure.get('source_summary') or governance.get('lineage_summary'),
                max_length=80,
            )
            error_message = cls._compact_text(
                failure.get('error_message') or failure.get('status_message'),
                max_length=80,
            )
            return {
                'title': f'{base["label"]} 故障处置',
                'steps': [
                    f'先核对失败阶段 {latest_phase}，确认输入来源 {source_summary} 与当前工作单一致。',
                    f'进入 {action_label}，优先处理错误摘要：{error_message}。',
                    '处置后重新提交任务，并确认新的版本快照已经写入审计与资产台账。',
                ],
            }

        if latest_job and latest_job.get('status') in {'queued', 'running'}:
            events = latest_job.get('events') or []
            latest_event = events[-1] if isinstance(events, list) and events else {}
            phase = cls._compact_text(
                latest_event.get('phase') or latest_job.get('status') or 'running',
            )
            progress = int(latest_job.get('progress') or 0)
            source_summary = cls._compact_text(
                cls._source_summary(str(latest_job.get('type') or ''), latest_job),
                max_length=80,
            )
            return {
                'title': f'{base["label"]} 作业跟进',
                'steps': [
                    f'当前先盯住阶段 {phase}，持续跟进作业进度 {progress}%。',
                    f'复核当前输入来源 {source_summary}，避免作业完成后生成错误资产。',
                    '作业完成后立刻复查版本血缘、结果摘要和回放入口是否齐全。',
                ],
            }

        if status == 'action':
            return {
                'title': f'{base["label"]} 资产补齐',
                'steps': [
                    f'先进入 {action_label}，完成该链路至少一次成功任务，建立基础资产。',
                    cls._compact_text(governance.get('recommended_action'), max_length=96),
                    '补齐后回到驾驶舱确认版本、台账和回放入口都已生成。',
                ],
            }

        if status == 'watch':
            failure_summary = cls._compact_text(
                governance.get('failure_summary') or '最近存在失败来源',
                max_length=88,
            )
            return {
                'title': f'{base["label"]} 恢复观察',
                'steps': [
                    f'先确认最近失败来源：{failure_summary}。',
                    f'继续观察最新版本 {governance.get("latest_version") or "--"} 是否已经恢复到稳定基线。',
                    '如再次失败或进入 SLA 风险，直接切回对应工作台重新处置。',
                ],
            }

        return {
            'title': f'{base["label"]} 基线检查',
            'steps': list(base['healthy_steps']),
        }

    @staticmethod
    def _timeline_node(
        *,
        kind: str,
        title: str,
        detail: str,
        timestamp: Any,
        level: str,
        badge: str,
        source_label: str = '--',
        version_tag: str = '--',
        phase_label: str = '--',
    ) -> Dict[str, Any]:
        return {
            'kind': kind,
            'title': title,
            'detail': detail,
            'timestamp': HistoryService._as_iso(timestamp),
            'level': level,
            'badge': badge,
            'source_label': source_label,
            'version_tag': version_tag,
            'phase_label': phase_label,
        }

    @staticmethod
    def _status_label(status: str) -> str:
        return {
            'incident': '故障待处置',
            'active': '作业进行中',
            'action': '资产待补齐',
            'watch': '需要观察',
            'healthy': '链路健康',
        }.get(status, '链路更新')

    @classmethod
    def _priority_score(
        cls,
        *,
        status: str,
        governance: Dict[str, Any],
        failure: Dict[str, Any] | None,
        latest_job: Dict[str, Any] | None,
    ) -> int:
        if failure:
            return 300
        if latest_job and latest_job.get('status') == 'running':
            return 220
        if latest_job and latest_job.get('status') == 'queued':
            return 200
        risk_level = str(governance.get('risk_level') or '')
        if status == 'action' or risk_level == 'action':
            return 160
        if status == 'watch' or risk_level == 'watch':
            return 120
        return 60

    @classmethod
    def _focus_summary(
        cls,
        *,
        status: str,
        governance: Dict[str, Any],
        failure: Dict[str, Any] | None,
        latest_job: Dict[str, Any] | None,
    ) -> tuple[str, str]:
        if failure:
            return (
                '优先处理失败链路',
                cls._compact_text(
                    f"{failure.get('latest_phase') or '--'} · {failure.get('error_message') or failure.get('status_message') or '--'}",
                    max_length=72,
                ),
            )
        if latest_job and latest_job.get('status') in {'queued', 'running'}:
            latest_event = None
            events = latest_job.get('events') or []
            if isinstance(events, list) and events:
                latest_event = events[-1]
            return (
                '跟进活跃作业',
                cls._compact_text(
                    f"{(latest_event or {}).get('phase') or latest_job.get('status') or '--'} · {latest_job.get('progress') or 0}%",
                    max_length=72,
                ),
            )
        if status == 'action':
            return (
                '补齐关键资产',
                cls._compact_text(governance.get('recommended_action'), max_length=72),
            )
        if status == 'watch':
            return (
                '观察恢复情况',
                cls._compact_text(governance.get('failure_summary'), max_length=72),
            )
        return (
            '维持当前基线',
            cls._compact_text(governance.get('lineage_summary'), max_length=72),
        )

    @classmethod
    def _focus_target(
        cls,
        *,
        key: str,
        status: str,
        failure: Dict[str, Any] | None,
        latest_job: Dict[str, Any] | None,
    ) -> str:
        latest_phase = ''
        if latest_job:
            events = latest_job.get('events') or []
            latest_event = events[-1] if isinstance(events, list) and events else {}
            latest_phase = str(
                latest_event.get('phase') or latest_job.get('status') or '',
            ).lower()
        elif failure:
            latest_phase = str(failure.get('latest_phase') or '').lower()

        if key == 'dataset':
            if status == 'action':
                return 'dataset_current_asset'
            if failure:
                return 'dataset_governance_decision'
            if latest_job and latest_job.get('status') in {'queued', 'running'}:
                return 'dataset_job_panel'
            if status == 'watch':
                return 'dataset_drift_report'
            return 'dataset_results'

        if key == 'model':
            if failure or (latest_job and latest_job.get('status') in {'queued', 'running'}):
                return 'model_runtime'
            return 'model_registry'

        if key == 'knowledge':
            if failure or (latest_job and latest_job.get('status') in {'queued', 'running'}):
                return 'knowledge_runtime'
            return 'knowledge_registry'

        if key == 'optimization':
            if 'explain' in latest_phase:
                return 'optimization_explainability'
            if 'solver' in latest_phase or 'forecast' in latest_phase or 'aggregation' in latest_phase:
                return 'optimization_solver'
            if failure or (latest_job and latest_job.get('status') in {'queued', 'running'}):
                return 'optimization_job_panel'
            if status == 'watch':
                return 'optimization_constraint'
            return 'optimization_registry'

        return 'workspace'

    @staticmethod
    def _focus_target_label(target: str) -> str:
        return {
            'dataset_current_asset': '当前资产',
            'dataset_reference_asset': '基线资产',
            'dataset_drift_report': '漂移报告',
            'dataset_governance_decision': '治理决策',
            'dataset_results': '分析结果',
            'dataset_job_panel': '数据任务',
            'model_runtime': '训练运行态',
            'model_registry': '模型注册表',
            'knowledge_runtime': '知识运行态',
            'knowledge_registry': '知识注册表',
            'optimization_solver': '求解器运维',
            'optimization_constraint': '约束压力',
            'optimization_explainability': '解释性前哨',
            'optimization_registry': '优化注册表',
            'optimization_job_panel': '优化任务',
            'workspace': '工作台',
        }.get(target, '工作台')

    @classmethod
    def _section_target(cls, *, key: str, focus_target: str) -> str:
        if key == 'dataset':
            if focus_target == 'dataset_job_panel':
                return 'data_analysis_operations'
            return 'data_analysis_results'

        if key in {'model', 'knowledge'}:
            if focus_target in {'model_runtime', 'knowledge_runtime'}:
                return 'ai_lab_runtime'
            return 'ai_lab_assets'

        if key == 'optimization':
            if focus_target == 'optimization_registry':
                return 'optimization_assets'
            return 'optimization_operations'

        return 'workspace'

    @staticmethod
    def _section_target_label(target: str) -> str:
        return {
            'data_analysis_operations': '运营态工作台',
            'data_analysis_results': '结果资产台',
            'ai_lab_runtime': '运行控制区',
            'ai_lab_assets': '资产治理区',
            'optimization_operations': '优化运维区',
            'optimization_assets': '资产注册表',
            'workspace': '工作台',
        }.get(target, '工作台')

    @staticmethod
    def _workspace_target(*, key: str, focus_target: str, section_target: str) -> str:
        if key == 'dataset':
            if focus_target == 'dataset_job_panel':
                return 'data_job_center'
            if focus_target in {
                'dataset_current_asset',
                'dataset_reference_asset',
                'dataset_drift_report',
                'dataset_governance_decision',
            }:
                return 'data_governance'
            return 'data_handoff'

        if key in {'model', 'knowledge'}:
            if section_target == 'ai_lab_runtime':
                return 'ai_runtime'
            return 'ai_assets'

        if key == 'optimization':
            if focus_target == 'optimization_job_panel':
                return 'optimization_job_center'
            if section_target == 'optimization_assets':
                return 'optimization_registry'
            return 'optimization_operations'

        return 'workspace'

    @staticmethod
    def _workspace_target_label(target: str) -> str:
        return {
            'audit_center': '历史与审计',
            'data_job_center': '分析任务中心',
            'data_governance': '资产治理板',
            'data_handoff': '分析交接板',
            'ai_runtime': 'AI 运行控制区',
            'ai_assets': 'AI 资产治理区',
            'optimization_job_center': '优化任务中心',
            'optimization_registry': '优化注册表',
            'optimization_operations': '优化运维板',
            'workspace': '工作台',
        }.get(target, '工作台')

    @staticmethod
    def _card_target_label(target: str) -> str:
        return {
            'strategy': '执行策略',
            'job_health': '任务健康',
            'asset_route': '资产路线',
            'asset_quality': '资产质量',
            'schema_topology': 'Schema 拓扑',
            'field_distribution': '字段分布',
            'risk_digest': '风险摘要',
            'next_actions': '下一步动作',
            'current_asset': '当前资产',
            'reference_asset': '基线资产',
            'drift_report': '漂移报告',
            'governance_decision': '治理结论',
            'runtime_product': '运行产物',
            'version_timeline': '版本轨迹',
            'registry_snapshot': '注册表快照',
            'solver_health': '求解器健康',
            'constraint_pressure': '约束压力',
            'explainability_probe': '解释性前哨',
            'recent_artifact': '最近产物',
            'registry_summary': '注册表摘要',
            'latest_snapshot': '最新快照',
            'summary': '当前卡片',
        }.get(target, '当前卡片')

    @classmethod
    def _workspace_brief(
        cls,
        *,
        workspace_target: str,
        section_target: str,
        incident_target: str,
        focus_target: str,
        latest_job: Dict[str, Any] | None,
        governance: Dict[str, Any],
        failure: Dict[str, Any] | None,
    ) -> str:
        if workspace_target in {
            'data_job_center',
            'optimization_job_center',
            'ai_runtime',
        }:
            if latest_job:
                events = latest_job.get('events') or []
                latest_event = events[-1] if isinstance(events, list) and events else {}
                phase = cls._compact_text(
                    latest_event.get('phase') or latest_job.get('status'),
                )
                progress = int(latest_job.get('progress') or 0)
                return f'{phase} · {progress}% · {cls._section_target_label(section_target)}'
            if failure:
                return cls._compact_text(
                    (
                        f"{failure.get('latest_phase') or '--'}"
                        f" · {failure.get('error_message') or failure.get('status_message') or '--'}"
                    ),
                    max_length=88,
                )

        if workspace_target == 'data_governance':
            return cls._compact_text(
                governance.get('recommended_action')
                or (
                    f"{cls._incident_target_label(incident_target)}"
                    f" · {cls._focus_target_label(focus_target)}"
                ),
                max_length=88,
            )

        if workspace_target in {'data_handoff', 'ai_assets', 'optimization_registry'}:
            return cls._compact_text(
                f"{governance.get('latest_label') or '--'} · {cls._section_target_label(section_target)}",
                max_length=88,
            )

        if workspace_target == 'optimization_operations':
            return cls._compact_text(
                f"{cls._incident_target_label(incident_target)} · {cls._focus_target_label(focus_target)}",
                max_length=88,
            )

        return cls._compact_text(
            f"{cls._section_target_label(section_target)} · {cls._focus_target_label(focus_target)}",
            max_length=88,
        )

    @staticmethod
    def _narrative_target(
        *,
        focus_target: str,
        is_overdue: bool,
        status: str,
        failure: Dict[str, Any] | None,
    ) -> str:
        if is_overdue:
            return 'sla'
        if failure and status == 'incident':
            return 'action'
        if focus_target in {
            'dataset_job_panel',
            'model_runtime',
            'knowledge_runtime',
            'optimization_job_panel',
        }:
            return 'job'
        if focus_target in {
            'dataset_governance_decision',
            'dataset_drift_report',
            'optimization_solver',
            'optimization_constraint',
            'optimization_explainability',
        }:
            return 'action'
        if focus_target in {
            'dataset_current_asset',
            'dataset_reference_asset',
            'dataset_results',
            'model_registry',
            'knowledge_registry',
            'optimization_registry',
        }:
            return 'target'
        return 'target'

    @staticmethod
    def _narrative_target_label(target: str) -> str:
        return {
            'lineage': '版本血缘',
            'target': '目标落点',
            'sla': '响应时限',
            'activity': '最近活动',
            'job': '活跃作业',
            'action': '当前处置',
        }.get(target, '目标落点')

    @staticmethod
    def _incident_target(
        *,
        focus_target: str,
        is_overdue: bool,
        status: str,
        failure: Dict[str, Any] | None,
        latest_job: Dict[str, Any] | None,
        activity: Dict[str, Any] | None,
    ) -> str:
        if is_overdue:
            return 'sla'
        if failure and status == 'incident':
            return 'failure'
        if latest_job and latest_job.get('status') in {'queued', 'running'}:
            return 'runtime'
        if focus_target in {
            'dataset_current_asset',
            'dataset_reference_asset',
            'dataset_results',
            'model_registry',
            'knowledge_registry',
            'optimization_registry',
        }:
            return 'asset'
        if activity:
            return 'activity'
        return 'focus'

    @staticmethod
    def _incident_target_label(target: str) -> str:
        return {
            'sla': '值班时限',
            'failure': '失败链路',
            'runtime': '活跃作业',
            'asset': '资产状态',
            'activity': '最近活动',
            'focus': '当前焦点',
        }.get(target, '当前焦点')

    @classmethod
    def _incident_brief(
        cls,
        *,
        incident_target: str,
        focus_target: str,
        section_target: str,
        focus_detail: str,
        escalation: Dict[str, Any],
        latest_job: Dict[str, Any] | None,
        activity: Dict[str, Any] | None,
        governance: Dict[str, Any],
        failure: Dict[str, Any] | None,
    ) -> str:
        if incident_target == 'sla':
            deadline_at = cls._as_datetime(escalation.get('sla_deadline_at'))
            deadline_label = deadline_at.strftime('%m-%d %H:%M') if deadline_at else '--'
            return (
                f"{escalation.get('escalation_state_label') or '--'}"
                f" · due {deadline_label}"
                f" · {governance.get('escalation_label') or '--'}"
            )

        if incident_target == 'failure' and failure:
            phase = cls._compact_text(failure.get('latest_phase'))
            source = cls._compact_text(
                failure.get('source_summary') or failure.get('error_message'),
                max_length=80,
            )
            return f'{phase} · {source}'

        if incident_target == 'runtime' and latest_job:
            events = latest_job.get('events') or []
            latest_event = events[-1] if isinstance(events, list) and events else {}
            phase = cls._compact_text(
                latest_event.get('phase') or latest_job.get('status'),
            )
            progress = int(latest_job.get('progress') or 0)
            return f'{phase} · {progress}%'

        if incident_target == 'activity' and activity:
            return cls._compact_text(
                f"{activity.get('title') or '--'} · {activity.get('source') or '--'}",
                max_length=88,
            )

        if incident_target == 'asset':
            return cls._compact_text(
                f"{cls._section_target_label(section_target)} · {cls._focus_target_label(focus_target)} · {governance.get('latest_label') or '--'}",
                max_length=88,
            )

        return cls._compact_text(
            f"{cls._focus_target_label(focus_target)} · {focus_detail}",
            max_length=88,
        )

    @staticmethod
    def _disposition_target(
        *,
        focus_target: str,
        is_overdue: bool,
        status: str,
        failure: Dict[str, Any] | None,
    ) -> str:
        if is_overdue:
            return 'sla'
        if failure and status == 'incident':
            return 'failure'
        if focus_target in {'dataset_governance_decision', 'optimization_constraint'}:
            return 'governance'
        if focus_target in {
            'dataset_job_panel',
            'model_runtime',
            'knowledge_runtime',
            'optimization_job_panel',
        }:
            return 'job'
        if focus_target in {
            'model_registry',
            'knowledge_registry',
            'optimization_registry',
        }:
            return 'replay'
        return 'focus'

    @staticmethod
    def _disposition_target_label(target: str) -> str:
        return {
            'governance': '风险建议',
            'focus': '当前焦点',
            'sla': '响应时限',
            'replay': '回放库存',
            'failure': '失败链路',
            'job': '活跃作业',
        }.get(target, '当前焦点')

    @classmethod
    def _escalation_summary(
        cls,
        *,
        status: str,
        governance: Dict[str, Any],
        failure: Dict[str, Any] | None,
        latest_job: Dict[str, Any] | None,
        activity: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        sla_minutes = int(governance.get('sla_minutes') or 0)
        reference_at = None

        if failure:
            reference_at = cls._as_datetime(
                failure.get('completed_at') or failure.get('submitted_at'),
            )
        elif latest_job:
            events = latest_job.get('events') or []
            latest_event = events[-1] if isinstance(events, list) and events else {}
            reference_at = cls._as_datetime(
                latest_event.get('timestamp')
                or latest_job.get('started_at')
                or latest_job.get('submitted_at'),
            )
        elif status in {'action', 'watch'} and activity:
            reference_at = cls._as_datetime(activity.get('created_at'))

        deadline_at = (
            reference_at + timedelta(minutes=sla_minutes)
            if reference_at is not None and sla_minutes > 0
            else None
        )
        now = datetime.utcnow()
        elapsed_minutes = (
            max(int((now - reference_at).total_seconds() // 60), 0)
            if reference_at is not None
            else 0
        )
        overdue_minutes = (
            max(int((now - deadline_at).total_seconds() // 60), 0)
            if deadline_at is not None
            else 0
        )
        is_overdue = deadline_at is not None and now > deadline_at

        if is_overdue:
            escalation_tier = 2
            escalation_state_label = 'SLA 已超时'
        elif status == 'incident' or (
            sla_minutes > 0 and elapsed_minutes >= max(int(sla_minutes * 0.8), 1)
        ):
            escalation_tier = 1
            escalation_state_label = '临近升级阈值'
        else:
            escalation_tier = 0
            escalation_state_label = '仍在 SLA 内'

        return {
            'sla_deadline_at': HistoryService._as_iso(deadline_at),
            'elapsed_minutes': elapsed_minutes,
            'overdue_minutes': overdue_minutes,
            'is_overdue': is_overdue,
            'escalation_tier': escalation_tier,
            'escalation_state_label': escalation_state_label,
        }

    @classmethod
    def _chain_timeline(
        cls,
        *,
        key: str,
        governance: Dict[str, Any],
        failure: Dict[str, Any] | None,
        activity: Dict[str, Any] | None,
        latest_job: Dict[str, Any] | None,
        datasets: List[Dict[str, Any]],
        models: List[Dict[str, Any]],
        knowledge_bases: List[Dict[str, Any]],
        optimizations: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        nodes: List[Dict[str, Any]] = []

        if key == 'dataset' and datasets:
            latest = datasets[0]
            nodes.append(
                cls._timeline_node(
                    kind='version',
                    title=f'数据资产 v{governance.get("latest_version") or "--"}',
                    detail=governance.get('lineage_summary') or '--',
                    timestamp=latest.get('created_at'),
                    level='info',
                    badge='ASSET',
                    source_label='dataset',
                    version_tag=governance.get('latest_version') or '--',
                    phase_label=cls._compact_text(latest.get('filename')),
                ),
            )
        elif key == 'model' and models:
            latest = models[0]
            nodes.append(
                cls._timeline_node(
                    kind='version',
                    title=f'模型版本 v{governance.get("latest_version") or "--"}',
                    detail=governance.get('lineage_summary') or '--',
                    timestamp=latest.get('completed_at'),
                    level='info',
                    badge='MODEL',
                    source_label='ml_train',
                    version_tag=governance.get('latest_version') or '--',
                    phase_label=cls._compact_text(latest.get('model_type')),
                ),
            )
        elif key == 'knowledge' and knowledge_bases:
            latest = knowledge_bases[0]
            nodes.append(
                cls._timeline_node(
                    kind='version',
                    title=f'知识快照 v{governance.get("latest_version") or "--"}',
                    detail=governance.get('lineage_summary') or '--',
                    timestamp=latest.get('completed_at'),
                    level='info',
                    badge='KNOW',
                    source_label='rag_ingest',
                    version_tag=governance.get('latest_version') or '--',
                    phase_label=cls._compact_text(latest.get('collection')),
                ),
            )
        elif key == 'optimization' and optimizations:
            latest = optimizations[0]
            nodes.append(
                cls._timeline_node(
                    kind='version',
                    title=f'优化快照 v{governance.get("latest_version") or "--"}',
                    detail=governance.get('lineage_summary') or '--',
                    timestamp=latest.get('completed_at'),
                    level='info',
                    badge='OPT',
                    source_label='optimization',
                    version_tag=governance.get('latest_version') or '--',
                    phase_label=cls._compact_text(latest.get('target_date')),
                ),
            )

        if latest_job:
            latest_event = None
            events = latest_job.get('events') or []
            if isinstance(events, list) and events:
                latest_event = events[-1]
            nodes.append(
                cls._timeline_node(
                    kind='job',
                    title=f'{latest_job.get("type") or "job"} · {latest_job.get("status") or "--"}',
                    detail=f'{(latest_event or {}).get("phase") or "--"} · {latest_job.get("progress") or 0}%',
                    timestamp=(latest_event or {}).get('timestamp')
                    or latest_job.get('started_at')
                    or latest_job.get('submitted_at'),
                    level='warning'
                    if latest_job.get('status') in {'queued', 'running'}
                    else 'info',
                    badge='JOB',
                    source_label=str(latest_job.get('type') or '--'),
                    version_tag=governance.get('latest_version') or '--',
                    phase_label=str((latest_event or {}).get('phase') or latest_job.get('status') or '--'),
                ),
            )

        if activity:
            nodes.append(
                cls._timeline_node(
                    kind='activity',
                    title=str(activity.get('title') or '最新活动'),
                    detail=f"{activity.get('source') or '--'} · {activity.get('status') or '--'}",
                    timestamp=activity.get('created_at'),
                    level='info',
                    badge='AUDIT',
                    source_label=str(activity.get('source') or '--'),
                    version_tag=governance.get('latest_version') or '--',
                    phase_label=str(activity.get('status') or '--'),
                ),
            )

        if failure:
            nodes.append(
                cls._timeline_node(
                    kind='failure',
                    title=str(failure.get('label') or '失败链路'),
                    detail=f"{failure.get('error_code') or '--'} · {failure.get('failure_source') or failure.get('source_summary') or '--'}",
                    timestamp=failure.get('completed_at') or failure.get('submitted_at'),
                    level='error',
                    badge='FAIL',
                    source_label=str(failure.get('job_type') or '--'),
                    version_tag=failure.get('latest_version') or '--',
                    phase_label=str(failure.get('latest_phase') or '--'),
                ),
            )

        nodes.sort(key=lambda item: item.get('timestamp') or '', reverse=True)
        return nodes[:3]

    @classmethod
    def build_asset_summary(
        cls,
        uid: str,
        limit: int = 6,
        recent_activity: List[Dict[str, Any]] | None = None,
        recent_jobs: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        history_records = HistoryService.get_user_history(uid, limit=limit)
        training_jobs = JobService.list_jobs(uid, job_type='ml_train', limit=limit)
        rag_jobs = JobService.list_jobs(uid, job_type='rag_ingest', limit=limit)
        optimization_jobs = JobService.list_jobs(uid, job_type='optimization', limit=limit)
        failed_analysis_jobs = JobService.list_jobs(uid, job_type='analysis', status='failed', limit=2)
        failed_training_jobs = JobService.list_jobs(uid, job_type='ml_train', status='failed', limit=2)
        failed_rag_jobs = JobService.list_jobs(uid, job_type='rag_ingest', status='failed', limit=2)
        failed_optimization_jobs = JobService.list_jobs(uid, job_type='optimization', status='failed', limit=2)

        datasets = []
        for record in history_records:
            summary = record.get('summary') or {}
            basic_info = summary.get('basic_info') or {}
            datasets.append(
                {
                    'id': record.get('id'),
                    'filename': record.get('filename', 'Unknown'),
                    'quality_score': record.get('quality_score'),
                    'rows': basic_info.get('rows'),
                    'columns': basic_info.get('columns'),
                    'storage_url': record.get('storage_url'),
                    'created_at': HistoryService._as_iso(record.get('created_at')),
                }
            )

        models = []
        for job in training_jobs:
            if job.get('status') != 'succeeded':
                continue
            result = job.get('result') or {}
            input_payload = job.get('input') or {}
            models.append(
                {
                    'job_id': job.get('job_id'),
                    'version': cls._version_label(job.get('completed_at') or job.get('submitted_at')),
                    'model_type': result.get('model_type') or input_payload.get('model_type'),
                    'model_path': result.get('model_path'),
                    'target_column': result.get('target_column') or input_payload.get('target_column'),
                    'storage_path': input_payload.get('storage_path'),
                    'attempt_count': job.get('attempt_count'),
                    'max_attempts': job.get('max_attempts'),
                    'completed_at': job.get('completed_at'),
                }
            )

        knowledge_bases = []
        for job in rag_jobs:
            if job.get('status') != 'succeeded':
                continue
            result = job.get('result') or {}
            input_payload = job.get('input') or {}
            knowledge_bases.append(
                {
                    'job_id': job.get('job_id'),
                    'version': cls._version_label(job.get('completed_at') or job.get('submitted_at')),
                    'collection': result.get('collection') or input_payload.get('collection_name'),
                    'storage_path': result.get('storage_path') or input_payload.get('storage_path'),
                    'count': result.get('count'),
                    'reset': input_payload.get('reset'),
                    'completed_at': job.get('completed_at'),
                }
            )

        optimizations = []
        for job in optimization_jobs:
            if job.get('status') != 'succeeded':
                continue
            result = job.get('result') or {}
            input_payload = job.get('input') or {}
            optimization = result.get('optimization') or {}
            summary = optimization.get('summary') or {}
            optimizations.append(
                {
                    'job_id': job.get('job_id'),
                    'version': cls._version_label(job.get('completed_at') or job.get('submitted_at')),
                    'target_date': input_payload.get('target_date'),
                    'initial_soc': input_payload.get('initial_soc'),
                    'battery_capacity': input_payload.get('battery_capacity'),
                    'battery_power': input_payload.get('battery_power'),
                    'savings': summary.get('savings'),
                    'savings_percent': summary.get('savings_percent'),
                    'completed_at': job.get('completed_at'),
                }
            )

        failure_chains = [
            *[cls._failure_chain_item('analysis', job) for job in failed_analysis_jobs],
            *[cls._failure_chain_item('ml_train', job) for job in failed_training_jobs],
            *[cls._failure_chain_item('rag_ingest', job) for job in failed_rag_jobs],
            *[cls._failure_chain_item('optimization', job) for job in failed_optimization_jobs],
        ]
        failure_chains.sort(
            key=lambda item: item.get('completed_at') or item.get('submitted_at') or '',
            reverse=True,
        )
        latest_failure_by_key = {
            key: next((item for item in failure_chains if item.get('key') == key), None)
            for key in ('dataset', 'model', 'knowledge', 'optimization')
        }
        latest_activity_by_key = {
            key: next(
                (
                    activity
                    for activity in (recent_activity or [])
                    if cls._activity_key(activity) == key
                ),
                None,
            )
            for key in ('dataset', 'model', 'knowledge', 'optimization')
        }
        latest_job_by_key = {
            key: next(
                (job for job in (recent_jobs or []) if cls._job_key(job) == key),
                None,
            )
            for key in ('dataset', 'model', 'knowledge', 'optimization')
        }

        governance = [
            cls._governance_item(
                key='dataset',
                label='数据资产',
                asset_count=HistoryService.count_history_records(uid),
                failed_jobs=JobService.count_jobs(uid, job_type='analysis', status='failed'),
                latest_version=cls._version_label(datasets[0].get('created_at')) if datasets else '--',
                latest_label=datasets[0].get('filename', '--') if datasets else '--',
                lineage_summary=cls._dataset_lineage(datasets[0]) if datasets else '--',
                failure_summary=(latest_failure_by_key.get('dataset') or {}).get('source_summary', '--'),
                missing_message='先完成一次分析归档，沉淀可复用数据资产。',
                recovery_message='最近有 {failed_jobs} 个分析失败项，建议先检查上传和分析日志。',
                healthy_message='数据资产链路正常，可继续做对比、漂移和协作交接。',
                action_label='打开数据分析',
                owner_label=cls.CHAIN_OPERATIONS_CONFIG['dataset']['owner_label'],
                sla_minutes=cls.CHAIN_OPERATIONS_CONFIG['dataset']['sla_minutes'],
                escalation_label=cls.CHAIN_OPERATIONS_CONFIG['dataset']['escalation_label'],
            ),
            cls._governance_item(
                key='model',
                label='模型资产',
                asset_count=JobService.count_jobs(uid, job_type='ml_train', status='succeeded'),
                failed_jobs=JobService.count_jobs(uid, job_type='ml_train', status='failed'),
                latest_version=models[0].get('version', '--') if models else '--',
                latest_label=models[0].get('model_type', '--') if models else '--',
                lineage_summary=cls._model_lineage(models[0]) if models else '--',
                failure_summary=(latest_failure_by_key.get('model') or {}).get('source_summary', '--'),
                missing_message='至少完成一次训练任务，才能形成可回填模型版本。',
                recovery_message='最近有 {failed_jobs} 个训练失败项，建议优先排查训练数据和目标列。',
                healthy_message='模型资产链路正常，可继续训练、回填和版本治理。',
                action_label='打开 AI Lab',
                owner_label=cls.CHAIN_OPERATIONS_CONFIG['model']['owner_label'],
                sla_minutes=cls.CHAIN_OPERATIONS_CONFIG['model']['sla_minutes'],
                escalation_label=cls.CHAIN_OPERATIONS_CONFIG['model']['escalation_label'],
            ),
            cls._governance_item(
                key='knowledge',
                label='知识快照',
                asset_count=JobService.count_jobs(uid, job_type='rag_ingest', status='succeeded'),
                failed_jobs=JobService.count_jobs(uid, job_type='rag_ingest', status='failed'),
                latest_version=knowledge_bases[0].get('version', '--') if knowledge_bases else '--',
                latest_label=knowledge_bases[0].get('collection', '--') if knowledge_bases else '--',
                lineage_summary=cls._knowledge_lineage(knowledge_bases[0]) if knowledge_bases else '--',
                failure_summary=(latest_failure_by_key.get('knowledge') or {}).get('source_summary', '--'),
                missing_message='先完成一次知识库构建，生成可问答的知识快照。',
                recovery_message='最近有 {failed_jobs} 个知识库任务失败，建议排查文档路径和集合模式。',
                healthy_message='知识快照链路正常，可继续问答调试和快照治理。',
                action_label='打开 AI Lab',
                owner_label=cls.CHAIN_OPERATIONS_CONFIG['knowledge']['owner_label'],
                sla_minutes=cls.CHAIN_OPERATIONS_CONFIG['knowledge']['sla_minutes'],
                escalation_label=cls.CHAIN_OPERATIONS_CONFIG['knowledge']['escalation_label'],
            ),
            cls._governance_item(
                key='optimization',
                label='优化快照',
                asset_count=JobService.count_jobs(uid, job_type='optimization', status='succeeded'),
                failed_jobs=JobService.count_jobs(uid, job_type='optimization', status='failed'),
                latest_version=optimizations[0].get('version', '--') if optimizations else '--',
                latest_label=optimizations[0].get('target_date', '--') if optimizations else '--',
                lineage_summary=cls._optimization_lineage(optimizations[0]) if optimizations else '--',
                failure_summary=(latest_failure_by_key.get('optimization') or {}).get('source_summary', '--'),
                missing_message='先提交一次后台优化任务，沉淀可复盘的优化快照。',
                recovery_message='最近有 {failed_jobs} 个优化失败项，建议优先检查求解器和约束输入。',
                healthy_message='优化快照链路正常，可继续版本复盘和结果导出。',
                action_label='打开能源优化',
                owner_label=cls.CHAIN_OPERATIONS_CONFIG['optimization']['owner_label'],
                sla_minutes=cls.CHAIN_OPERATIONS_CONFIG['optimization']['sla_minutes'],
                escalation_label=cls.CHAIN_OPERATIONS_CONFIG['optimization']['escalation_label'],
            ),
        ]
        chain_summaries = [
            cls._chain_summary(
                key=item['key'],
                label=item['label'],
                governance=item,
                failure=latest_failure_by_key.get(item['key']),
                activity=latest_activity_by_key.get(item['key']),
                latest_job=latest_job_by_key.get(item['key']),
                timeline=cls._chain_timeline(
                    key=item['key'],
                    governance=item,
                    failure=latest_failure_by_key.get(item['key']),
                    activity=latest_activity_by_key.get(item['key']),
                    latest_job=latest_job_by_key.get(item['key']),
                    datasets=datasets,
                    models=models,
                    knowledge_bases=knowledge_bases,
                    optimizations=optimizations,
                ),
            )
            for item in governance
        ]

        return {
            'inventory': {
                'dataset_assets': HistoryService.count_history_records(uid),
                'model_assets': JobService.count_jobs(uid, job_type='ml_train', status='succeeded'),
                'knowledge_assets': JobService.count_jobs(uid, job_type='rag_ingest', status='succeeded'),
                'optimization_assets': JobService.count_jobs(uid, job_type='optimization', status='succeeded'),
            },
            'datasets': datasets,
            'models': models[:limit],
            'knowledge_bases': knowledge_bases[:limit],
            'optimizations': optimizations[:limit],
            'failure_chains': failure_chains[: max(limit, 4)],
            'governance': governance,
            'chain_summaries': chain_summaries,
        }

    @classmethod
    def _build_duty_summary(
        cls,
        *,
        asset_summary: Dict[str, Any],
        service_statuses: List[Dict[str, Any]],
        alerts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        chains = asset_summary.get('chain_summaries') or []
        ordered_chains = sorted(
            chains,
            key=lambda item: int(item.get('priority_score') or 0),
            reverse=True,
        )
        focus_chain = ordered_chains[0] if ordered_chains else {}
        degraded_systems = len(
            [status for status in service_statuses if status.get('status') != 'ok']
        )
        incident_count = len(
            [chain for chain in chains if chain.get('status') == 'incident']
        )
        active_count = len(
            [chain for chain in chains if chain.get('status') == 'active']
        )
        overdue_count = len(
            [chain for chain in chains if bool(chain.get('is_overdue'))]
        )
        escalated_count = len(
            [chain for chain in chains if int(chain.get('escalation_tier') or 0) > 0]
        )
        watch_count = len(
            [chain for chain in chains if chain.get('status') in {'watch', 'action'}]
        )
        duty_actions = cls._build_duty_actions(
            focus_chain=focus_chain if focus_chain else None,
            chains=ordered_chains,
        )

        return {
            'incident_count': incident_count,
            'active_count': active_count,
            'watch_count': watch_count,
            'overdue_count': overdue_count,
            'escalated_count': escalated_count,
            'alert_count': len(alerts),
            'degraded_system_count': degraded_systems,
            'focus_chain_key': focus_chain.get('key') or '',
            'focus_chain_label': focus_chain.get('label') or '--',
            'focus_workspace_target': focus_chain.get('workspace_target') or 'workspace',
            'focus_workspace_target_label': focus_chain.get('workspace_target_label') or '工作台',
            'focus_card_target': focus_chain.get('card_target') or 'summary',
            'focus_card_target_label': focus_chain.get('card_target_label') or '当前卡片',
            'focus_incident_target': focus_chain.get('incident_target') or 'focus',
            'focus_incident_target_label': focus_chain.get('incident_target_label') or '当前焦点',
            'focus_watch': focus_chain.get('incident_brief')
            or focus_chain.get('workspace_brief')
            or '当前暂无高优先级链路',
            'focus_owner_label': focus_chain.get('owner_label') or '--',
            'focus_escalation_state_label': focus_chain.get('escalation_state_label')
            or '--',
            'overview_actions': duty_actions['overview_actions'],
            'audit_actions': duty_actions['audit_actions'],
        }

    @classmethod
    def _build_duty_actions(
        cls,
        *,
        focus_chain: Dict[str, Any] | None,
        chains: List[Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        chain_map = {
            str(chain.get('key') or ''): chain
            for chain in chains
            if str(chain.get('key') or '')
        }

        overview_actions: List[Dict[str, Any]] = []
        audit_actions: List[Dict[str, Any]] = []

        if focus_chain:
            overview_actions.append(
                cls._duty_action(
                    command='open_workspace',
                    label=focus_chain.get('action_label') or '打开工作台',
                    tone='primary',
                    chain_key=focus_chain.get('key') or '',
                    chain_label=focus_chain.get('label') or '--',
                    workspace_target=focus_chain.get('workspace_target') or 'workspace',
                    card_target=focus_chain.get('card_target') or 'summary',
                    incident_target=focus_chain.get('incident_target') or 'focus',
                    workspace_brief=focus_chain.get('workspace_brief') or '--',
                ),
            )
            audit_actions.append(
                cls._duty_action(
                    command='open_workspace',
                    label=focus_chain.get('action_label') or '打开工作台',
                    tone='primary',
                    chain_key=focus_chain.get('key') or '',
                    chain_label=focus_chain.get('label') or '--',
                    workspace_target=focus_chain.get('workspace_target') or 'workspace',
                    card_target=focus_chain.get('card_target') or 'summary',
                    incident_target=focus_chain.get('incident_target') or 'focus',
                    workspace_brief=focus_chain.get('workspace_brief') or '--',
                ),
            )

        for key in ('dataset', 'optimization', 'model', 'knowledge'):
            if focus_chain and key == focus_chain.get('key'):
                continue
            overview_actions.append(
                cls._workspace_action_for_chain(chain_map.get(key), key=key),
            )

        overview_actions.append(
            cls._duty_action(
                command='open_audit',
                label='查看历史与审计',
                tone='outline',
                chain_key=(focus_chain or {}).get('key') or '',
                chain_label='历史与审计',
                workspace_target='audit_center',
                card_target='summary',
                incident_target='focus',
                workspace_brief='历史与审计 · 查看统一事件流、资产矩阵和处置 Runbook。',
            ),
        )

        if focus_chain:
            audit_actions.extend(
                [
                    cls._duty_action(
                        command='filter_failed',
                        label='仅看失败链路',
                        tone='tonal',
                        chain_key=focus_chain.get('key') or '',
                        chain_label=focus_chain.get('label') or '--',
                        workspace_target='audit_center',
                        card_target='summary',
                        incident_target='failure',
                        workspace_brief='历史与审计 · 过滤失败任务与异常链路。',
                    ),
                    cls._duty_action(
                        command='filter_running',
                        label='仅看运行中',
                        tone='outline',
                        chain_key=focus_chain.get('key') or '',
                        chain_label=focus_chain.get('label') or '--',
                        workspace_target='audit_center',
                        card_target='summary',
                        incident_target='runtime',
                        workspace_brief='历史与审计 · 聚焦运行中任务和当前活跃作业。',
                    ),
                ]
            )

        audit_actions.append(
            cls._duty_action(
                command='clear_filters',
                label='清空筛选',
                tone='outline',
                chain_key=(focus_chain or {}).get('key') or '',
                chain_label='历史与审计',
                workspace_target='audit_center',
                card_target='summary',
                incident_target='focus',
                workspace_brief='历史与审计 · 恢复默认筛选并查看完整事件流。',
            ),
        )

        return {
            'overview_actions': overview_actions[:5],
            'audit_actions': audit_actions[:4],
        }

    @classmethod
    def _workspace_action_for_chain(
        cls,
        chain: Dict[str, Any] | None,
        *,
        key: str,
    ) -> Dict[str, Any]:
        defaults = cls.DUTY_ACTION_DEFAULTS[key]
        return cls._duty_action(
            command='open_workspace',
            label=defaults['label'],
            tone=defaults['tone'],
            chain_key=key,
            chain_label=(chain or {}).get('label') or cls.RUNBOOK_BASE[key]['label'],
            workspace_target=(chain or {}).get('workspace_target')
            or defaults['workspace_target'],
            card_target=(chain or {}).get('card_target') or defaults['card_target'],
            incident_target=(chain or {}).get('incident_target')
            or defaults['incident_target'],
            workspace_brief=(chain or {}).get('workspace_brief')
            or defaults['workspace_brief'],
        )

    @classmethod
    def _duty_action(
        cls,
        *,
        command: str,
        label: str,
        tone: str,
        chain_key: str,
        chain_label: str,
        workspace_target: str,
        card_target: str,
        incident_target: str,
        workspace_brief: str,
    ) -> Dict[str, Any]:
        return {
            'command': command,
            'label': label,
            'tone': tone,
            'chain_key': chain_key,
            'chain_label': chain_label,
            'workspace_target': workspace_target,
            'workspace_target_label': cls._workspace_target_label(workspace_target),
            'card_target': card_target,
            'card_target_label': cls._card_target_label(card_target),
            'incident_target': incident_target,
            'incident_target_label': cls._incident_target_label(incident_target),
            'workspace_brief': cls._compact_text(workspace_brief, max_length=96),
        }

    @classmethod
    def build_summary(cls, uid: str) -> Dict[str, Any]:
        activity = HistoryService.get_recent_activity(uid, limit=8)
        jobs = JobService.list_jobs(uid, limit=12)
        recent_assets = HistoryService.get_recent_assets(uid, limit=5)
        asset_summary = cls.build_asset_summary(
            uid,
            limit=4,
            recent_activity=activity,
            recent_jobs=jobs,
        )
        cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_jobs_24h = JobService.count_jobs(uid, submitted_after=cutoff)
        failed_jobs = JobService.count_jobs(uid, status='failed')
        dataset_count = HistoryService.count_history_records(uid)
        analysis_count = HistoryService.count_activity(uid, activity_type='analysis', status='success')
        model_count = JobService.count_jobs(uid, job_type='ml_train', status='succeeded')

        service_statuses = cls._service_statuses()
        alerts: List[Dict[str, Any]] = []
        for status in service_statuses:
            if status['status'] != 'ok':
                alerts.append(
                    {
                        'severity': 'warning' if status['status'] == 'warning' else 'error',
                        'title': f"{status['label']} 状态异常",
                        'message': status['message'],
                    }
                )
        inventory = asset_summary.get('inventory') or {}
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
                    'asset_key': 'dataset',
                }
            )
        if inventory.get('model_assets', 0) == 0:
            alerts.append(
                {
                    'severity': 'warning',
                    'title': '暂无模型资产',
                    'message': '至少完成一次训练任务后，AI Lab 才会登记可复用模型版本。',
                    'asset_key': 'model',
                }
            )
        if inventory.get('knowledge_assets', 0) == 0:
            alerts.append(
                {
                    'severity': 'warning',
                    'title': '暂无知识快照',
                    'message': '知识助手当前没有可回放的知识库快照，建议先执行一次 ingest。',
                    'asset_key': 'knowledge',
                }
            )
        if inventory.get('optimization_assets', 0) == 0:
            alerts.append(
                {
                    'severity': 'info',
                    'title': '暂无优化快照',
                    'message': '当前还没有登记到资产台账的优化快照，可通过后台优化任务沉淀版本。',
                    'asset_key': 'optimization',
                }
            )

        duty_summary = cls._build_duty_summary(
            asset_summary=asset_summary,
            service_statuses=service_statuses,
            alerts=alerts,
        )

        return {
            'system_status': service_statuses,
            'kpis': {
                'dataset_count': dataset_count,
                'analysis_count': analysis_count,
                'model_count': model_count,
                'jobs_24h': recent_jobs_24h,
                'failed_jobs': failed_jobs,
            },
            'duty_summary': duty_summary,
            'recent_jobs': jobs[:6],
            'recent_assets': recent_assets,
            'recent_history': activity,
            'asset_summary': asset_summary,
            'alerts': alerts,
        }
