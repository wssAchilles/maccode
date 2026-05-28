export interface Track {
  tracker_id: number;
  class_id: number;
  class_name: string;
  confidence: number;
  xyxy: [number, number, number, number];
  first_seen_frame: number;
  last_seen_frame: number;
  speed_kmh: number | null;
}

export interface ZoneStats {
  name: string;
  in_count: number;
  out_count: number;
}

export interface FrameReport {
  frame_index: number;
  timestamp_sec: number;
  fps: number;
  active_tracks: Track[];
  zone_stats: ZoneStats[];
  total_in: number;
  total_out: number;
}

export interface CumulativeStats {
  total_frames: number;
  total_unique_tracks: number;
  zone_stats: ZoneStats[];
  avg_fps: number;
  avg_speed_kmh: number | null;
  processing_time_sec: number;
}
