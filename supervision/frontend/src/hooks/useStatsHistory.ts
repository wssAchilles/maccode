import { useCallback, useEffect, useState } from "react";

import { getCumulativeStats, getHistoryStats } from "../api/stats";
import type { CumulativeStats, FrameReport } from "../types/frameReport";
import { demoCumulativeStats, demoFrameReport } from "../utils/constants";

export function useStatsHistory() {
  const [history, setHistory] = useState<FrameReport[]>([demoFrameReport]);
  const [cumulative, setCumulative] = useState<CumulativeStats>(demoCumulativeStats);

  const refresh = useCallback(async () => {
    try {
      const [nextHistory, nextCumulative] = await Promise.all([
        getHistoryStats(),
        getCumulativeStats()
      ]);
      setHistory(nextHistory);
      setCumulative(nextCumulative);
    } catch {
      setHistory([demoFrameReport]);
      setCumulative(demoCumulativeStats);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { history, cumulative, refresh };
}
