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
      speed_kmh: 5.0539737597193515,
      speed_uncertainty_kmh: 0.4,
      speed_confidence: 0.92,
      speed_confidence_interval_kmh: [4.65, 5.45],
      position_rmse_m: 0.05,
      ground_x_m: 4.0,
      ground_y_m: 2.4,
      velocity_x_mps: 0.96,
      velocity_y_mps: 1.36,
      heading_deg: 54.65,
      acceleration_mps2: 1.14
    }
  ],
  zone_stats: [{ name: "main_gate", in_count: 1, out_count: 0 }],
  total_in: 1,
  total_out: 0,
  calibration_quality: "excellent",
  traffic_flow: {
    flow_q_veh_per_hour: 120,
    density_k_veh_per_km: 2,
    space_mean_speed_kmh: 5.0539737597193515,
    congestion_level: "stable_flow",
    greenshields_speed_kmh: 39.2,
    model_explanation: "Greenshields model"
  },
  regional_people_count: {
    region_name: "main_gate",
    people_count: 0,
    unit: "person",
    estimation_method: "direct_detection_count",
    density_integral_triggered: false,
    model_reference: "Model 9 + Model 10 fallback policy"
  },
  infrastructure_semantics: {
    traffic_light_count: 1,
    stop_sign_count: 0,
    traffic_light_state: "unknown",
    violation_on_crosswalk: false,
    dynamic_vehicle_count: 1,
    semantic_note: "Signal-state classification is reserved for a dedicated ROI classifier.",
    model_reference: "Model 10 infrastructure routing"
  },
  safety_metrics: {
    vehicle_pair_count: 0,
    min_time_headway_sec: null,
    min_time_to_collision_sec: null,
    risk_level: "nominal",
    model_reference: "trajectory geometry + relative speed safety surrogate"
  }
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
