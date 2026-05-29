export interface ProcessingTask {
  task_id: string;
  source: string;
  status: "running" | "stopped";
  frame_count: number;
  uploaded_filename?: string;
  stored_filename?: string;
  path?: string;
  content_type?: string | null;
  size_bytes?: number;
  analysis_status?: "demo" | "real_video" | "fallback_demo";
  analysis_source?: string;
  analysis_device?: string | null;
  analysis_error?: string | null;
  analysis_clip?: string | null;
  calibration_source?: string | null;
  processed_video_path?: string | null;
  processed_video_url?: string | null;
}

export interface VideoSample {
  name: string;
  source: string;
  profile: string;
  role?: string | null;
  selection_reason?: string | null;
  tuning?: Record<string, unknown>;
  size_bytes: number;
}
