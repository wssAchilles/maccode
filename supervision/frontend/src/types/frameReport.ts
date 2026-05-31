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
  physics_valid: boolean;
  quality_label:
    | "stable"
    | "warming_up"
    | "low_confidence"
    | "rejected"
    | "not_applicable"
    | string;
  rejection_reason: string | null;
  track_age_frames: number;
  window_residual_m: number | null;
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
  calibration_diagnostics: CalibrationDiagnostics | null;
  homography_grid: HomographyGrid | null;
  traffic_flow: TrafficFlowResult | null;
  regional_people_count: RegionalPeopleCount | null;
  infrastructure_semantics: InfrastructureSemantics | null;
  safety_metrics: SafetyMetrics | null;
}

export interface HomographyGridLine {
  kind: "longitudinal" | "lateral" | string;
  world_start: [number, number];
  world_end: [number, number];
  pixel_start: [number, number];
  pixel_end: [number, number];
}

export interface HomographyGrid {
  frame_width: number;
  frame_height: number;
  spacing_m: number;
  world_width_m: number;
  world_length_m: number;
  generated_from: string;
  calibration_source: string;
  calibration_trusted: boolean;
  pixel_rmse_px: number;
  world_rmse_m: number;
  validation_max_error_px: number | null;
  road_plane_polygon_world: Array<[number, number]> | null;
  lines: HomographyGridLine[];
}

export interface CalibrationDiagnostics {
  homography_model: string;
  calibration_source?: string;
  camera_profile_id?: string | null;
  camera_profile_display_name?: string | null;
  camera_profile_role?: string | null;
  profile_reuse_note?: string | null;
  profile_polygon_zones?: Array<Record<string, unknown>>;
  profile_traffic_light_rois?: Array<Record<string, unknown>>;
  profile_risk_areas?: Array<Record<string, unknown>>;
  auto_calibration?: {
    auto_calibration_confidence: number;
    candidate_lines: Array<Record<string, unknown>>;
    vanishing_points: Array<[number, number]>;
    scale_prior_used: string | null;
    quality_issues: string[];
    selected_strategy: string;
    evidence_sources: string[];
    homography_proposal: {
      method: string;
      candidate_points: Array<{
        pixel: [number, number];
        world: [number, number];
      }>;
      inlier_count: number;
      reprojection_rmse: number;
      condition_number: number;
      calibration_quality: string;
    } | null;
  } | null;
  frame_geometry_evidence?: {
    frame_index: number;
    frame_width: number;
    frame_height: number;
    candidate_line_count: number;
    candidate_lines: Array<Record<string, unknown>>;
  } | null;
  calibration_quality: string;
  calibration_trusted?: boolean;
  declared_calibration_trusted?: boolean;
  pixel_to_world_rmse_m?: number;
  world_to_pixel_rmse_px?: number;
  validation_max_error_px?: number | null;
  reprojection_rmse_px: number;
  inlier_count: number;
  condition_number: number;
  position_rmse_m: number;
  timestamp_uncertainty_sec?: number;
  scale_uncertainty_pct?: number;
  speed_band_kmh?: [number | null, number | null];
  space_mean_speed_band_kmh?: [number | null, number | null];
  error_sources: string[];
  model_reference: string;
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
  direct_detection_count?: number;
  integrated_people_count?: number;
  density_people_per_sqm?: number;
  peak_density_people_per_sqm?: number;
  unit: string;
  estimation_method: string;
  density_integral_triggered: boolean;
  crowding_level?: string;
  density_field?: {
    cell_size_m: number;
    kernel_bandwidth_m: number;
    cells_x: number;
    cells_y: number;
    visible_area_sqm: number;
    raw_integral_people?: number;
    occlusion_correction_factor?: number;
  };
  model_reference: string;
}

export interface InfrastructureSemantics {
  traffic_light_count: number;
  stop_sign_count: number;
  traffic_light_state: string;
  traffic_light_state_source?: string;
  traffic_light_states?: Array<Record<string, unknown>>;
  configured_traffic_light_rois?: Array<Record<string, unknown>>;
  violation_on_crosswalk: boolean;
  red_light_violation_candidate_track_ids?: number[];
  dynamic_vehicle_count: number;
  semantic_note: string;
  model_reference: string;
}

export interface SafetyMetrics {
  vehicle_pair_count: number;
  min_time_headway_sec: number | null;
  min_time_to_collision_sec: number | null;
  speed_limit_kmh?: number;
  speeding_track_ids?: number[];
  red_light_violation_track_ids?: number[];
  configured_polygon_zones?: Array<Record<string, unknown>>;
  configured_risk_areas?: Array<Record<string, unknown>>;
  rule_source?: string;
  risk_level: string;
  model_reference: string;
}
