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


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
        return {
            'projection_version': 'shell-runtime-v1',
            'generated_at': _utc_now_iso(),
            'summary': summary,
            'approval_queue': {
                'jobs': approval_jobs,
                'count': len(approval_jobs) if isinstance(approval_jobs, list) else 0,
            },
            'control_tasks': {
                'items': control_tasks,
                'count': len(control_tasks) if isinstance(control_tasks, list) else 0,
            },
            'compute_governance': {
                'policy': compute_policy,
                'activity': compute_activity,
            },
            'degraded_sections': degraded_sections,
        }
