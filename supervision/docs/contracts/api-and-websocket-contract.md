# API and WebSocket Contract Freeze

Phase 3 will expose the domain contracts below without changing their field names.

## REST

- `POST /api/video/upload` returns `{ "task_id": str, "path": str }`.
- `POST /api/video/process` returns `{ "task_id": str }`.
- `GET /api/stats/realtime` returns `FrameReport`.
- `GET /api/stats/cumulative` returns `CumulativeStats`.
- `GET /api/zones` returns `ZoneConfig[]`.
- `PUT /api/zones` accepts `ZoneConfig[]`.
- `POST /api/ai/report` accepts statistics JSON and returns Markdown report text.

## WebSocket

- `WS /ws/stream` server messages use `{ "type": "frame_report", "data": FrameReport }`.
- `speed_kmh` stays nullable so frontend code can distinguish unknown speed from zero speed.
