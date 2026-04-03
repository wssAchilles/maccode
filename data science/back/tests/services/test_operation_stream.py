"""Tests for operation SSE helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

BACK_ROOT = Path(__file__).resolve().parents[2]
if str(BACK_ROOT) not in sys.path:
    sys.path.insert(0, str(BACK_ROOT))

from services.operation_stream import format_sse, stream_operation_events


class OperationStreamTestCase(unittest.TestCase):
    def test_format_sse_includes_event_id_and_payload(self):
        frame = format_sse(
            {'status': 'running', 'progress': 30},
            event='operation.state',
            event_id='state-1',
        )

        self.assertIn('event: operation.state', frame)
        self.assertIn('id: state-1', frame)
        self.assertIn('"status": "running"', frame)
        self.assertTrue(frame.endswith('\n\n'))

    def test_stream_operation_events_emits_snapshot_state_and_closed(self):
        states = [
            {
                'job_id': 'op-1',
                'status': 'running',
                'progress': 10,
                'current_step': {'phase': 'prepare_dataset'},
            },
            {
                'job_id': 'op-1',
                'status': 'succeeded',
                'progress': 100,
                'current_step': {'phase': 'generate_report'},
            },
        ]
        fetch_count = {'value': 0}

        def fetch_operation():
            index = min(fetch_count['value'], len(states) - 1)
            fetch_count['value'] += 1
            return states[index]

        def list_events():
            if fetch_count['value'] < 2:
                return []
            return [
                {
                    'type': 'operation.completed',
                    'phase': 'completed',
                    'status': 'succeeded',
                    'message': 'done',
                    'progress': 100,
                }
            ]

        frames = list(
            stream_operation_events(
                operation_id='op-1',
                fetch_operation=fetch_operation,
                list_events=list_events,
                poll_interval_s=0,
                max_duration_s=1,
            )
        )

        self.assertTrue(any('event: operation.snapshot' in frame for frame in frames))
        self.assertTrue(any('event: operation.state' in frame for frame in frames))
        self.assertTrue(any('event: operation.completed' in frame for frame in frames))
        self.assertTrue(any('event: operation.closed' in frame for frame in frames))


if __name__ == '__main__':
    unittest.main()
