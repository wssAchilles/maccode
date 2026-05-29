import { useState } from "react";

import { startVideoProcessing, stopVideoProcessing, uploadVideoForProcessing } from "../api/video";
import type { ProcessingTask } from "../types/videoTask";

export function useVideoTask() {
  const [task, setTask] = useState<ProcessingTask | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function start(file: File) {
    setIsLoading(true);
    setError(null);
    try {
      const nextTask = await uploadVideoForProcessing(file);
      setTask(nextTask);
      return nextTask;
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "视频任务启动失败");
      return null;
    } finally {
      setIsLoading(false);
    }
  }

  async function startSource(source: string) {
    setIsLoading(true);
    setError(null);
    try {
      const nextTask = await startVideoProcessing(source);
      setTask(nextTask);
      return nextTask;
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "视频任务启动失败");
      return null;
    } finally {
      setIsLoading(false);
    }
  }

  async function stop() {
    if (!task) {
      return null;
    }
    setIsLoading(true);
    setError(null);
    try {
      const stopped = await stopVideoProcessing(task.task_id);
      setTask(stopped);
      return stopped;
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "视频任务停止失败");
      return null;
    } finally {
      setIsLoading(false);
    }
  }

  return { task, isLoading, error, start, startSource, stop };
}
