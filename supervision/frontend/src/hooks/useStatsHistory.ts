import { useCallback, useState } from "react";

import { getCumulativeStats, getHistoryStats } from "../api/stats";
import type { CumulativeStats, FrameReport } from "../types/frameReport";

export function useStatsHistory() {
  const [history, setHistory] = useState<FrameReport[]>([]);
  const [cumulative, setCumulative] = useState<CumulativeStats | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [nextHistory, nextCumulative] = await Promise.all([
        getHistoryStats(),
        getCumulativeStats()
      ]);
      setHistory(nextHistory);
      setCumulative(nextCumulative);
    } catch {
      setHistory([]);
      setCumulative(null);
    }
  }, []);

  return { history, cumulative, refresh };
}
