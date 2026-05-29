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
  points: CalibrationPoint[];
}

export interface CalibrationDiagnostics {
  homography_model: string;
  calibration_source: string;
  calibration_quality: string;
  reprojection_rmse_px: number;
  inlier_count: number;
  condition_number: number;
  inlier_mask: boolean[];
  position_rmse_m: number;
  scale_uncertainty_pct: number;
  world_width_m: number;
  world_length_m: number;
  model_reference: string;
  homography_grid?: HomographyGrid;
}

export interface CalibrationSaveResult {
  clip_name: string;
  source: "video_manual_preset";
  entry: CalibrationEntry;
  diagnostics: CalibrationDiagnostics;
  preset_path: string;
}
