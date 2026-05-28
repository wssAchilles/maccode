import { requestJson } from "./client";
import type { AIReportResult } from "../types/aiReport";
import type { FrameReport } from "../types/frameReport";

export function generateAIReport(stats: FrameReport) {
  return requestJson<AIReportResult>("/api/ai/report", {
    method: "POST",
    body: JSON.stringify({ stats })
  });
}
