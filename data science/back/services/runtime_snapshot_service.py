"""Shell runtime snapshot aggregation for shared control-plane read models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List

from services.compute_governance_activity_service import (
    ComputeGovernanceActivityService,
)
from services.compute_governance_status_service import (
    ComputeGovernanceStatusService,
)
from services.control_task_service import (
    ControlTaskBackendUnavailableError,
    ControlTaskService,
)
from services.dashboard_service import DashboardService
from services.job_service import JobBackendUnavailableError, JobService
from services.orchestrator_runtime_projection_service import (
    OrchestratorRuntimeProjectionService,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _merge_control_tasks(
    local_items: Any,
    projected_items: Any,
) -> List[Dict[str, Any]]:
    local_list = list(local_items) if isinstance(local_items, list) else []
    projected_list = list(projected_items) if isinstance(projected_items, list) else []
    if not projected_list:
        return local_list

    merged_by_id: Dict[str, Dict[str, Any]] = {}
    ordered_ids: List[str] = []

    for item in projected_list:
        if not isinstance(item, dict):
            continue
        task_id = str(item.get('id') or '')
        if not task_id:
            continue
        merged_by_id[task_id] = item
        ordered_ids.append(task_id)

    for item in local_list:
        if not isinstance(item, dict):
            continue
        task_id = str(item.get('id') or '')
        if not task_id:
            continue
        if task_id not in merged_by_id:
            merged_by_id[task_id] = item
            ordered_ids.append(task_id)

    return [merged_by_id[task_id] for task_id in ordered_ids if task_id in merged_by_id]


def _merge_degraded_sections(
    base: List[Dict[str, str]],
    incoming: Any,
) -> List[Dict[str, str]]:
    merged = list(base)
    seen = {
        (
            str(item.get('section') or ''),
            str(item.get('message') or ''),
        )
        for item in merged
        if isinstance(item, dict)
    }
    if not isinstance(incoming, list):
        return merged

    for item in incoming:
        if not isinstance(item, dict):
            continue
        section = str(item.get('section') or '')
        message = str(item.get('message') or '')
        key = (section, message)
        if not section or not message or key in seen:
            continue
        merged.append({'section': section, 'message': message})
        seen.add(key)
    return merged


class RuntimeSnapshotService:
    """Build a shell-facing snapshot of shared control-plane state."""

    @staticmethod
    def _safe_section(
        *,
        section: str,
        degraded: List[Dict[str, str]],
        callback: Callable[[], Any],
        fallback: Any,
    ) -> Any:
        try:
            return callback()
        except (ControlTaskBackendUnavailableError, JobBackendUnavailableError) as exc:
            degraded.append({'section': section, 'message': str(exc)})
            return fallback
        except Exception as exc:  # pragma: no cover - defensive aggregation
            degraded.append({'section': section, 'message': str(exc)})
            return fallback

    @classmethod
    def build_shell_snapshot(
        cls,
        uid: str,
        *,
        control_task_limit: int = 6,
        approval_limit: int = 20,
        compute_activity_limit: int = 8,
    ) -> Dict[str, Any]:
        degraded_sections: List[Dict[str, str]] = []
        summary = cls._safe_section(
            section='dashboard_summary',
            degraded=degraded_sections,
            callback=lambda: DashboardService.build_summary(uid),
            fallback={},
        )
        approval_jobs = cls._safe_section(
            section='approval_queue',
            degraded=degraded_sections,
            callback=lambda: JobService.list_jobs(
                uid,
                status='awaiting_approval',
                limit=approval_limit,
                scope='control_plane',
            ),
            fallback=[],
        )
        control_tasks = cls._safe_section(
            section='control_tasks',
            degraded=degraded_sections,
            callback=lambda: ControlTaskService.list_control_tasks(limit=control_task_limit),
            fallback=[],
        )
        control_plane_projection = cls._safe_section(
            section='control_plane_projection',
            degraded=degraded_sections,
            callback=lambda: OrchestratorRuntimeProjectionService.get_snapshot(uid),
            fallback={},
        )
        compute_policy = cls._safe_section(
            section='compute_policy',
            degraded=degraded_sections,
            callback=ComputeGovernanceStatusService.get_policy_view,
            fallback={},
        )
        compute_activity = cls._safe_section(
            section='compute_activity',
            degraded=degraded_sections,
            callback=lambda: ComputeGovernanceActivityService.list_recent_activity(
                uid,
                limit=compute_activity_limit,
            ),
            fallback=[],
        )
        projected_control_tasks = (
            control_plane_projection.get('control_tasks', {}).get('items')
            if isinstance(control_plane_projection, dict)
            else None
        )
        merged_control_tasks = _merge_control_tasks(control_tasks, projected_control_tasks)
        degraded_sections = _merge_degraded_sections(
            degraded_sections,
            control_plane_projection.get('degraded_sections')
            if isinstance(control_plane_projection, dict)
            else None,
        )
        return {
            'projection_version': 'shell-runtime-v2',
            'generated_at': _utc_now_iso(),
            'summary': summary,
            'approval_queue': {
                'jobs': approval_jobs,
                'count': len(approval_jobs) if isinstance(approval_jobs, list) else 0,
            },
            'control_tasks': {
                'items': merged_control_tasks,
                'count': len(merged_control_tasks),
            },
            'compute_governance': {
                'policy': compute_policy,
                'activity': compute_activity,
            },
            'control_plane': dict(control_plane_projection.get('control_plane') or {})
            if isinstance(control_plane_projection, dict)
            else {},
            'degraded_sections': degraded_sections,
        }
