import { requestJson } from "./client";
import type { ProcessingTask, VideoSample } from "../types/videoTask";

export function startVideoProcessing(source: string) {
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

export function listVideoSamples() {
  return requestJson<VideoSample[]>("/api/video/samples");
}

export function stopVideoProcessing(taskId: string) {
  return requestJson<ProcessingTask>(`/api/video/stop/${taskId}`, {
    method: "POST"
  });
}

export function getVideoStatus(taskId: string) {
  return requestJson<ProcessingTask>(`/api/video/status/${taskId}`);
}
