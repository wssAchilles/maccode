export interface Track {
  tracker_id: number;
  class_id: number;
  class_name: string;
  confidence: number;
  xyxy: [number, number, number, number];
  first_seen_frame: number;
  last_seen_frame: number;
  speed_kmh: number | null;
  speed_uncertainty_kmh: number | null;
  speed_confidence: number | null;
  speed_confidence_interval_kmh: [number, number] | null;
  position_rmse_m: number | null;
  ground_x_m: number | null;
  ground_y_m: number | null;
  velocity_x_mps: number | null;
  velocity_y_mps: number | null;
  heading_deg: number | null;
  acceleration_mps2: number | null;
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
  calibration_quality: string | null;
  traffic_flow: TrafficFlowResult | null;
  regional_people_count: RegionalPeopleCount | null;
  infrastructure_semantics: InfrastructureSemantics | null;
  safety_metrics: SafetyMetrics | null;
}

export interface CumulativeStats {
  total_frames: number;
  total_unique_tracks: number;
  zone_stats: ZoneStats[];
  avg_fps: number;
  avg_speed_kmh: number | null;
  processing_time_sec: number;
  avg_speed_confidence?: number | null;
}

export interface TrafficFlowResult {
  flow_q_veh_per_hour: number;
  density_k_veh_per_km: number;
  space_mean_speed_kmh: number | null;
  congestion_level: string;
  greenshields_speed_kmh: number;
  model_explanation: string;
}

export interface RegionalPeopleCount {
  region_name: string;
  people_count: number;
  unit: string;
  estimation_method: string;
  density_integral_triggered: boolean;
  model_reference: string;
}

export interface InfrastructureSemantics {
  traffic_light_count: number;
  stop_sign_count: number;
  traffic_light_state: string;
  violation_on_crosswalk: boolean;
  dynamic_vehicle_count: number;
  semantic_note: string;
  model_reference: string;
}

export interface SafetyMetrics {
  vehicle_pair_count: number;
  min_time_headway_sec: number | null;
  min_time_to_collision_sec: number | null;
  risk_level: string;
  model_reference: string;
}
