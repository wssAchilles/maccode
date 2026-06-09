from __future__ import annotations

import csv

from scripts.create_user_sample import keep_user, write_user_sample


def test_user_sample_keeps_or_drops_whole_users(tmp_path):
    source = tmp_path / "events.csv"
    rows = [
        {"event_time": "2019-11-01 00:00:00", "event_type": "view", "product_id": "1", "user_id": user_id, "user_session": f"s-{user_id}-{idx}"}
        for user_id in ["u1", "u2", "u3", "u4", "u5"]
        for idx in range(3)
    ]
    with source.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    target = tmp_path / "sample.csv"
    write_user_sample([source], target, percent=50)

    with target.open("r", encoding="utf-8", newline="") as handle:
        sampled_rows = list(csv.DictReader(handle))
    sampled_users = {row["user_id"] for row in sampled_rows}

    assert sampled_users == {user_id for user_id in ["u1", "u2", "u3", "u4", "u5"] if keep_user(user_id, 50)}
    assert all(sum(1 for row in sampled_rows if row["user_id"] == user_id) == 3 for user_id in sampled_users)
