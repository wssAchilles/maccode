import { useRef, useState } from "react";

import { startVideoProcessing, stopVideoProcessing, uploadVideoForProcessing } from "../api/video";
import type { ProcessingTask } from "../types/videoTask";

export function useVideoTask() {
  const [task, setTask] = useState<ProcessingTask | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  async function start(file: File) {
    abortControllerRef.current?.abort();
    const abortController = new AbortController();
    abortControllerRef.current = abortController;
    setIsLoading(true);
    setError(null);
    try {
      const nextTask = await uploadVideoForProcessing(file, abortController.signal);
      setTask(nextTask);
      return nextTask;
    } catch (exc) {
      if (exc instanceof DOMException && exc.name === "AbortError") {
        return null;
      }
      setError(exc instanceof Error ? exc.message : "视频任务启动失败");
      return null;
    } finally {
      if (abortControllerRef.current === abortController) {
        abortControllerRef.current = null;
      }
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
    if (isLoading && abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsLoading(false);
      return null;
    }
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

  function clear() {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setTask(null);
    setError(null);
    setIsLoading(false);
  }

  return { task, isLoading, error, start, startSource, stop, clear };
}
