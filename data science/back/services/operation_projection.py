"""Serialization and projection helpers for operations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services.history_service import HistoryService


def coerce_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    iso_value = HistoryService._as_iso(value)
    if not iso_value:
        return None
    try:
        parsed = datetime.fromisoformat(str(iso_value))
    except Exception:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def serialize_operation(record: Dict[str, Any]) -> Dict[str, Any]:
    serialized = dict(record)
    serialized['id'] = str(serialized.get('operation_id') or serialized.get('job_id') or '')
    serialized['job_id'] = str(serialized.get('job_id') or serialized.get('operation_id') or '')
    serialized['operation_id'] = serialized['job_id']
    for field in ('submitted_at', 'started_at', 'completed_at'):
        serialized[field] = HistoryService._as_iso(serialized.get(field))
    current_step = serialized.get('current_step')
    if isinstance(current_step, dict):
        serialized['current_step'] = serialize_step(current_step)
    raw_steps = serialized.get('steps')
    if isinstance(raw_steps, list):
        serialized['steps'] = [serialize_step(step) for step in raw_steps if isinstance(step, dict)]
    raw_events = serialized.get('events')
    if isinstance(raw_events, list):
        serialized['events'] = [serialize_event(event) for event in raw_events if isinstance(event, dict)]
    raw_artifacts = serialized.get('artifacts')
    if isinstance(raw_artifacts, list):
        serialized['artifacts'] = [
            serialize_artifact(artifact)
            for artifact in raw_artifacts
            if isinstance(artifact, dict)
        ]
    approval_state = serialized.get('approval_state')
    if isinstance(approval_state, dict):
        serialized['approval_state'] = {
            **approval_state,
            'approved_at': HistoryService._as_iso(approval_state.get('approved_at')),
        }
    serialized['session_projection'] = build_session_projection(serialized)
    return serialized


def serialize_step(step: Dict[str, Any]) -> Dict[str, Any]:
    return {
        **step,
        'started_at': HistoryService._as_iso(step.get('started_at')),
        'ended_at': HistoryService._as_iso(step.get('ended_at')),
    }


def serialize_event(event: Dict[str, Any]) -> Dict[str, Any]:
    return {
        **event,
        'timestamp': HistoryService._as_iso(event.get('timestamp') or event.get('timestamp_iso')),
    }


def serialize_artifact(artifact: Dict[str, Any]) -> Dict[str, Any]:
    return {
        **artifact,
        'created_at': HistoryService._as_iso(artifact.get('created_at')),
    }


def build_session_projection(record: Dict[str, Any]) -> Dict[str, Any]:
    events = record.get('events')
    events_list = events if isinstance(events, list) else []
    steps = record.get('steps')
    steps_list = steps if isinstance(steps, list) else []
    artifacts = record.get('artifacts')
    artifacts_list = artifacts if isinstance(artifacts, list) else []
    latest_event = _latest_event(events_list)
    current_step = record.get('current_step')
    current_step_label = _current_step_label(current_step)
    latest_event_at = HistoryService._as_iso(
        latest_event.get('timestamp') if isinstance(latest_event, dict) else None
    )
    status = str(record.get('status') or 'queued')
    phase = _session_phase(record, status)
    last_transition_at = (
        latest_event_at
        or HistoryService._as_iso(record.get('completed_at'))
        or HistoryService._as_iso(record.get('started_at'))
        or HistoryService._as_iso(record.get('submitted_at'))
    )
    terminal = status in {'succeeded', 'failed', 'cancelled'}
    return {
        'phase': phase,
        'latest_event_type': str(latest_event.get('type') or '')
        if isinstance(latest_event, dict)
        else None,
        'latest_event_message': str(latest_event.get('message') or '')
        if isinstance(latest_event, dict)
        else None,
        'latest_event_at': latest_event_at,
        'last_transition_at': last_transition_at,
        'current_step_label': current_step_label,
        'event_count': len(events_list),
        'step_count': len(steps_list),
        'artifact_count': len(artifacts_list),
        'stream_recommended': not terminal,
        'terminal': terminal,
    }


def build_event(
    *,
    event_type: str,
    phase: str,
    status: str,
    message: str,
    progress: int,
    timestamp: Optional[str] = None,
    step: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    event = {
        'type': event_type,
        'phase': phase,
        'status': status,
        'message': message,
        'progress': progress,
        'timestamp': timestamp or now_iso(),
    }
    if step:
        event['step'] = step
    if extra:
        event.update(extra)
    return event


def _latest_event(events: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not events:
        return None
    latest: Optional[Dict[str, Any]] = None
    latest_time: Optional[datetime] = None
    for event in events:
        if not isinstance(event, dict):
            continue
        event_time = coerce_datetime(event.get('timestamp') or event.get('timestamp_iso'))
        if latest is None:
            latest = event
            latest_time = event_time
            continue
        if event_time and (latest_time is None or event_time >= latest_time):
            latest = event
            latest_time = event_time
        elif latest_time is None:
            latest = event
    return latest or events[-1]


def _current_step_label(step: Any) -> Optional[str]:
    if not isinstance(step, dict):
        return None
    phase = str(step.get('phase') or '').strip()
    tool_name = str(step.get('tool_name') or step.get('toolName') or '').strip()
    if phase and tool_name:
        return f'{phase} · {tool_name}'
    if tool_name:
        return tool_name
    if phase:
        return phase
    return None


def _session_phase(record: Dict[str, Any], status: str) -> str:
    approval_state = record.get('approval_state')
    if isinstance(approval_state, dict) and str(approval_state.get('state') or '') == 'pending':
        return 'awaiting_approval'
    if status in {'succeeded', 'failed', 'cancelled'}:
        return 'terminal'
    if status in {'queued', 'dispatching'}:
        return 'loading'
    if status in {'running', 'retrying'}:
        return 'live'
    return status or 'idle'


def duration_ms(started_at: Optional[str], ended_at: Optional[str]) -> Optional[int]:
    start_dt = coerce_datetime(started_at)
    end_dt = coerce_datetime(ended_at)
    if not start_dt or not end_dt:
        return None
    return max(int((end_dt - start_dt).total_seconds() * 1000), 0)


def finalize_step(
    step: Dict[str, Any],
    *,
    status: str,
    ended_at: str,
    progress: Optional[int] = None,
) -> Dict[str, Any]:
    finalized = {
        **step,
        'status': status,
        'ended_at': ended_at,
    }
    if progress is not None:
        finalized['progress'] = progress
    finalized['duration_ms'] = duration_ms(
        str(finalized.get('started_at') or ''),
        ended_at,
    )
    return finalized


def upsert_step_summary(steps: List[Dict[str, Any]], step: Dict[str, Any]) -> List[Dict[str, Any]]:
    phase = step.get('phase')
    updated: List[Dict[str, Any]] = []
    replaced = False
    for existing in steps:
        if not replaced and existing.get('phase') == phase:
            updated.append(step)
            replaced = True
        else:
            updated.append(existing)
    if not replaced:
        updated.append(step)
    return updated


def extract_artifacts_from_result(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    artifacts: List[Dict[str, Any]] = []
    if not isinstance(result, dict):
        return artifacts

    def add_if_present(key: str, artifact_type: str, name: str):
        value = result.get(key)
        if value:
            artifacts.append(
                {
                    'type': artifact_type,
                    'name': name,
                    'uri': str(value),
                    'metadata': {'source_key': key},
                }
            )

    add_if_present('storage_path', 'dataset', 'Source dataset')
    add_if_present('model_path', 'model', 'Trained model')
    add_if_present('firebase_model_path', 'model', 'Published model')
    add_if_present('history_record_id', 'history_record', 'Analysis history record')
    add_if_present('collection_name', 'knowledge_snapshot', 'Knowledge collection')
    add_if_present('collection', 'knowledge_snapshot', 'Knowledge collection')
    add_if_present('report_path', 'report', 'Operation report')

    explicit_artifacts = result.get('artifacts')
    if isinstance(explicit_artifacts, list):
        for item in explicit_artifacts:
            if isinstance(item, dict) and item.get('type') and item.get('name'):
                artifacts.append(
                    {
                        'type': str(item.get('type')),
                        'name': str(item.get('name')),
                        'uri': item.get('uri'),
                        'metadata': dict(item.get('metadata') or {}),
                    }
                )
    return artifacts
