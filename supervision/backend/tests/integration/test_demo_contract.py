from __future__ import annotations

import json

from scripts.generate_demo_report import generate_demo_report


def test_demo_report_matches_frontend_contract() -> None:
    payload = generate_demo_report()
    encoded = json.dumps(payload, ensure_ascii=False)
    decoded = json.loads(encoded)

    assert decoded["frame_index"] == 3
    assert decoded["active_tracks"][0]["tracker_id"] == 1
    assert decoded["active_tracks"][0]["speed_kmh"] > 0
    assert decoded["zone_stats"][0]["name"] == "main_gate"
    assert decoded["total_in"] == 1
