import { requestJson } from "./client";
import type { ProcessingTask } from "../types/videoTask";

export function startVideoProcessing(source = "demo://traffic") {
  return requestJson<ProcessingTask>("/api/video/process", {
    method: "POST",
    body: JSON.stringify({ source })
  });
}

export function stopVideoProcessing(taskId: string) {
  return requestJson<ProcessingTask>(`/api/video/stop/${taskId}`, {
    method: "POST"
  });
}

export function getVideoStatus(taskId: string) {
  return requestJson<ProcessingTask>(`/api/video/status/${taskId}`);
}
