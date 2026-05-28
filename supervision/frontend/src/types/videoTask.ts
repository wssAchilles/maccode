export interface ProcessingTask {
  task_id: string;
  source: string;
  status: "running" | "stopped";
  frame_count: number;
}
