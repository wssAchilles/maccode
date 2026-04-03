"""Tests for control-task validation helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

BACK_ROOT = Path(__file__).resolve().parents[2]
if str(BACK_ROOT) not in sys.path:
    sys.path.insert(0, str(BACK_ROOT))

from services.control_task_validation import (  # noqa: E402
    ControlTaskValidationError,
    normalize_dependencies,
    normalize_schedule,
)


class ControlTaskValidationTestCase(unittest.TestCase):
    def test_normalize_schedule_accepts_hourly_and_daily_formats(self):
        self.assertEqual(normalize_schedule('every 1 hour'), 'every 1 hours')
        self.assertEqual(normalize_schedule('every day 04:00'), 'every day 04:00 UTC')
        self.assertIsNone(normalize_schedule('manual'))
        self.assertIsNone(normalize_schedule(''))

    def test_normalize_schedule_rejects_unknown_format(self):
        with self.assertRaises(ControlTaskValidationError):
            normalize_schedule('daily at 5')

    def test_normalize_dependencies_rejects_duplicates(self):
        with self.assertRaises(ControlTaskValidationError):
            normalize_dependencies(['dataset_ready', 'dataset_ready'])

    def test_normalize_dependencies_rejects_invalid_identifier(self):
        with self.assertRaises(ControlTaskValidationError):
            normalize_dependencies(['dataset ready'])


if __name__ == '__main__':
    unittest.main()
