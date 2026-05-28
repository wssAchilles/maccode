import type { FrameReport } from "../types/frameReport";
import type { ZoneConfig } from "../types/zoneConfig";

export const demoFrameReport: FrameReport = {
  frame_index: 3,
  timestamp_sec: 2,
  fps: 24,
  active_tracks: [
    {
      tracker_id: 1,
      class_id: 2,
      class_name: "car",
      confidence: 0.89,
      xyxy: [30, 12, 50, 24],
      first_seen_frame: 1,
      last_seen_frame: 3,
      speed_kmh: 5.0539737597193515
    }
  ],
  zone_stats: [{ name: "main_gate", in_count: 1, out_count: 0 }],
  total_in: 1,
  total_out: 0
};

export const demoZones: ZoneConfig[] = [{ name: "main_gate", line_start: [0, 10], line_end: [80, 10] }];

export const demoCumulativeStats = {
  total_frames: 1,
  total_unique_tracks: 1,
  zone_stats: demoFrameReport.zone_stats,
  avg_fps: 24,
  avg_speed_kmh: 5.0539737597193515,
  processing_time_sec: 0
};
