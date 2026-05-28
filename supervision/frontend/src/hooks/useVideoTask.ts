import { useState } from "react";

import { startVideoProcessing, stopVideoProcessing, uploadVideoForProcessing } from "../api/video";
import type { ProcessingTask } from "../types/videoTask";

export function useVideoTask() {
  const [task, setTask] = useState<ProcessingTask | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function start(file?: File) {
    setIsLoading(true);
    try {
      const nextTask = file ? await uploadVideoForProcessing(file) : await startVideoProcessing();
      setTask(nextTask);
      return nextTask;
    } finally {
      setIsLoading(false);
    }
  }

  async function stop() {
    if (!task) {
      return null;
    }
    setIsLoading(true);
    try {
      const stopped = await stopVideoProcessing(task.task_id);
      setTask(stopped);
      return stopped;
    } finally {
      setIsLoading(false);
    }
  }

  return { task, isLoading, start, stop };
}
