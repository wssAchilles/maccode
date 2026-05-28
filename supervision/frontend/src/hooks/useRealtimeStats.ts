import { useCallback, useEffect, useState } from "react";

import { getRealtimeStats } from "../api/stats";
import type { FrameReport } from "../types/frameReport";
import { demoFrameReport } from "../utils/constants";

export function useRealtimeStats() {
  const [report, setReport] = useState<FrameReport>(demoFrameReport);
  const [status, setStatus] = useState<"demo" | "live" | "error">("demo");

  const refresh = useCallback(async () => {
    try {
      const data = await getRealtimeStats();
      setReport(data);
      setStatus("live");
    } catch {
      setStatus("demo");
    }
  }, []);

  useEffect(() => {
    let isMounted = true;
    getRealtimeStats()
      .then((data) => {
        if (isMounted) {
          setReport(data);
          setStatus("live");
        }
      })
      .catch(() => {
        if (isMounted) {
          setStatus("demo");
        }
      });

    return () => {
      isMounted = false;
      };
  }, []);

  return { report, status, refresh };
}
