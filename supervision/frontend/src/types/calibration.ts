import type { HomographyGrid } from "./frameReport";

export interface CalibrationPoint {
  pixel_x: number;
  pixel_y: number;
  world_x: number;
  world_y: number;
}

export interface CalibrationEntry {
  notes: string;
  position_rmse_floor_m: number;
  calibration_scale_uncertainty_pct: number;
  calibration_trusted?: boolean;
  scale_prior?: Record<string, unknown> | null;
  profile_notes?: string;
  road_plane_polygon_pixel?: Array<[number, number]>;
  road_plane_polygon_world?: Array<[number, number]>;
  validation_segments?: ValidationSegment[];
  points: CalibrationPoint[];
}

export interface ValidationSegment {
  name: string;
  pixel_start: [number, number];
  pixel_end: [number, number];
  world_start: [number, number];
  world_end: [number, number];
}

export interface CalibrationDiagnostics {
  homography_model: string;
  calibration_source: string;
  calibration_trusted?: boolean;
  declared_calibration_trusted?: boolean;
  calibration_quality: string;
  pixel_to_world_rmse_m?: number;
  world_to_pixel_rmse_px?: number;
  validation_max_error_px?: number | null;
  independent_validation_segment_count?: number;
  validation_segments_independent?: boolean;
  reprojection_rmse_px: number;
  inlier_count: number;
  condition_number: number;
  inlier_mask: boolean[];
  position_rmse_m: number;
  scale_uncertainty_pct: number;
  world_width_m: number;
  world_length_m: number;
  model_reference: string;
  error_sources?: string[];
  homography_grid?: HomographyGrid;
}

export interface CalibrationSaveResult {
  clip_name: string;
  source: "video_manual_preset";
  entry: CalibrationEntry;
  diagnostics: CalibrationDiagnostics;
  preset_path: string;
}
