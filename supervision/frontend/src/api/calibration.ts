import { requestJson } from "./client";
import type { CalibrationEntry, CalibrationSaveResult } from "../types/calibration";

interface SaveCalibrationPayload extends CalibrationEntry {
  clip_name: string;
  frame_width?: number;
  frame_height?: number;
  grid_spacing_m?: number;
}

export function getCalibrationPreset(clipName: string) {
  return requestJson<CalibrationEntry | null>(
    `/api/calibration/preset?clip_name=${encodeURIComponent(clipName)}`
  );
}

export function saveCalibrationPreset(payload: SaveCalibrationPayload) {
  return requestJson<CalibrationSaveResult>("/api/calibration/preset", {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}
