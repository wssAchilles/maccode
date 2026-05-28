import { requestJson } from "./client";
import type { ProcessingTask } from "../types/videoTask";

export function startVideoProcessing(source = "demo://traffic") {
  return requestJson<ProcessingTask>("/api/video/process", {
    method: "POST",
    body: JSON.stringify({ source })
  });
}

export function uploadVideoForProcessing(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  return requestJson<ProcessingTask>("/api/video/upload", {
    method: "POST",
    body: formData
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
