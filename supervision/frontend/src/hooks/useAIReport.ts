import { useState } from "react";

import { generateAIReport } from "../api/aiReport";
import type { AIReportResult } from "../types/aiReport";
import type { FrameReport } from "../types/frameReport";

export function useAIReport() {
  const [report, setReport] = useState<AIReportResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function run(stats: FrameReport) {
    setIsLoading(true);
    try {
      setReport(await generateAIReport(stats));
    } finally {
      setIsLoading(false);
    }
  }

  return { report, isLoading, run };
}
