export interface Track {
  tracker_id: number;
  class_id: number;
  class_name: string;
  confidence: number;
  xyxy?: [number, number, number, number] | null;
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
  raw_speed_kmh?: number | null;
  speed_stability_score?: number | null;
  speed_cv?: number | null;
  max_speed_jump_kmh?: number | null;
  speed_jump_p95_kmh?: number | null;
  acceleration_p95_mps2?: number | null;
  jerk_p95_mps3?: number | null;
  stability_label?: string | null;
  position_sigma_m?: number | null;
  position_covariance?: number[][] | null;
  measurement_source?: string | null;
  measurement_confidence?: number | null;
  local_scale_factor?: number | null;
  reconstructed?: boolean;
  bev_risk_level?: "trusted" | "caution" | "rejected" | string | null;
  bev_risk_reason?: string | null;
  local_scale_percentile?: number | null;
  contact_fusion_sources?: string[] | null;
  contact_fusion_weights?: Record<string, number> | null;
  contact_pixel_covariance?: [[number, number], [number, number]] | number[][] | null;
  contact_fusion_confidence?: number | null;
  tracking_integrity_state?: string | null;
  id_switch_risk?: number | null;
  speed_frozen?: boolean;
  integrity_rejection_reason?: string | null;
  speed_confidence_calibrated?: number | null;
  confidence_calibration_bin?: string | null;
  calibration_uncertainty_band_kmh?: [number | null, number | null] | null;
  motion_mode?: string | null;
  motion_mode_probability?: number | null;
  imm_speed_kmh?: number | null;
  tracklet_relinked?: boolean;
  tracklet_parent_id?: number | null;
  association_score?: number | null;
  association_rejection_reason?: string | null;
  plane_id?: string | null;
  contact_source?: string | null;
  world_position_covariance?: number[][] | null;
  speed_geometry_diagnostics?: Record<string, unknown> | null;
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
  bev_confidence_map?: BEVConfidenceMap | null;
  integrity_diagnostics?: IntegrityDiagnostics | null;
  trajectory_diagnostics?: TrajectoryDiagnostics | null;
  calibration_sensitivity?: CalibrationSensitivity | null;
  confidence_calibration_summary?: ConfidenceCalibrationSummary | null;
  tracklet_reassociation_summary?: TrackletReassociationSummary | null;
  model_comparison_benchmark?: ModelComparisonBenchmark | null;
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
  metric_speed_admitted?: boolean;
  metric_speed_gate_reason?: string | null;
  metric_planes?: Array<Record<string, unknown>>;
  selected_plane_id?: string | null;
  plane_validation_errors?: Record<string, number>;
  track_geometry_diagnostics?: Record<string, unknown>;
  pixel_to_world_rmse_m?: number;
  world_to_pixel_rmse_px?: number;
  validation_max_error_px?: number | null;
  camera_intrinsics?: Record<string, unknown> | null;
  distortion_coefficients?: number[] | Record<string, unknown> | null;
  undistorted_frame_size?: [number, number] | Record<string, unknown> | null;
  intrinsics_unverified?: boolean;
  runtime_homography_source?: string;
  calibration_candidates?: Array<Record<string, unknown>>;
  selected_calibration_candidate_id?: string | null;
  candidate_score_breakdown?: Record<string, unknown>;
  candidate_rejection_reasons?: Record<string, string[]>;
  calibration_sensitivity?: CalibrationSensitivity | null;
  calibration_candidate_score?: number | null;
  refinement_applied?: boolean;
  refinement_initial_rmse_m?: number | null;
  refinement_final_rmse_m?: number | null;
  refinement_iterations?: number | null;
  reprojection_rmse_px: number;
  inlier_count: number;
  condition_number: number;
  position_rmse_m: number;
  timestamp_uncertainty_sec?: number;
  local_error_model?: string;
  calibration_risk_gate?: string;
  scale_uncertainty_pct?: number;
  speed_band_kmh?: [number | null, number | null];
  space_mean_speed_band_kmh?: [number | null, number | null];
  error_sources: string[];
  model_reference: string;
}

export interface BEVConfidenceMap {
  frame_width: number;
  frame_height: number;
  p75_local_scale: number;
  p95_local_scale: number;
  risk_counts: Record<string, number>;
  risk_ratios: Record<string, number>;
  cells: Array<Record<string, unknown>>;
}

export interface IntegrityDiagnostics {
  tracking_integrity_state_counts?: Record<string, number>;
  id_switch_risk_count?: number;
  speed_frozen_count?: number;
  speed_frozen_ratio?: number;
  bev_checked_count?: number;
  bev_rejected_count?: number;
  bev_rejected_ratio?: number;
  contact_fusion_count?: number;
  contact_fusion_low_confidence_count?: number;
  contact_fusion_low_confidence_ratio?: number;
  model_reference?: string;
}

export interface CalibrationSensitivity {
  perturbation_px?: number;
  speed_sensitivity_p50?: number;
  speed_sensitivity_p95?: number;
  calibration_uncertainty_band_kmh?: [number | null, number | null] | Array<number | null>;
  rejected_ratio_delta?: number;
  sample_count?: number;
  model_reference?: string;
}

export interface ConfidenceCalibrationSummary {
  speed_track_count?: number;
  confidence_bins?: Record<string, number>;
  proxy_low_confidence_count?: number;
  proxy_low_confidence_ratio?: number;
  avg_calibrated_confidence?: number | null;
  model_reference?: string;
}

export interface TrackletReassociationSummary {
  candidate_count?: number;
  relinked_count?: number;
  rejected_count?: number;
  model_reference?: string;
}

export interface ModelComparisonBenchmark {
  baseline?: Record<string, number | null>;
  optimized?: Record<string, number | null>;
  gates?: Record<string, boolean>;
  model_reference?: string;
}

export interface TrajectoryDiagnostics {
  track_entry_count: number;
  reconstructed_track_entries: number;
  reconstructed_ratio: number;
  low_confidence_ratio: number;
  track_fragmentation_count: number;
  id_switch_risk_count?: number;
  speed_frozen_ratio?: number;
  bev_rejected_ratio?: number;
  contact_fusion_low_confidence_ratio?: number;
  tracklet_relinked_count?: number;
  calibrated_low_confidence_ratio?: number;
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
