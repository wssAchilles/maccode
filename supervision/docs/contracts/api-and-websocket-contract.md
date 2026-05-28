# API and WebSocket Contract Freeze

Phase 3 will expose the domain contracts below without changing their field names.

## REST

- `POST /api/video/upload` accepts multipart `file` and returns `{ "task_id": str, "status": "running", "source": "file://...", "path": str, "uploaded_filename": str, "size_bytes": int }`.
- `POST /api/video/process` returns `{ "task_id": str, "status": "running", "source": str, "frame_count": int }`.
- `GET /api/stats/realtime` returns `FrameReport`.
- `GET /api/stats/cumulative` returns `CumulativeStats`.
- `GET /api/zones` returns `ZoneConfig[]`.
- `PUT /api/zones` accepts `ZoneConfig[]`.
- `POST /api/ai/report` accepts statistics JSON plus optional `location_label`/`scene_tags` and returns Markdown report text with `dynamic_context`.

## WebSocket

- `WS /ws/stream` server messages use `{ "type": "frame_report", "data": FrameReport }`.
- `speed_kmh` stays nullable so frontend code can distinguish unknown speed from zero speed.
- `active_tracks[]` may include `speed_uncertainty_kmh`, `speed_confidence`, and `position_rmse_m`.
- `FrameReport` may include `calibration_quality` and `traffic_flow` for the mathematical defense layer.
