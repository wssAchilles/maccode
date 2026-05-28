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
}
