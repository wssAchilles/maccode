import { useCallback, useState } from "react";

import { getRealtimeStats } from "../api/stats";
import type { FrameReport } from "../types/frameReport";

export type RealtimeStatus = "idle" | "live" | "error";

export function useRealtimeStats() {
  const [report, setReport] = useState<FrameReport | null>(null);
  const [status, setStatus] = useState<RealtimeStatus>("idle");

  const refresh = useCallback(async () => {
    try {
      const data = await getRealtimeStats();
      setReport(data);
      setStatus("live");
    } catch {
      setStatus("error");
    }
  }, []);

  const clear = useCallback(() => {
    setReport(null);
    setStatus("idle");
  }, []);

  return { report, status, refresh, clear };
}
