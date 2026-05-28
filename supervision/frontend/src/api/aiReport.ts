import { requestJson } from "./client";
import type { AIReportResult } from "../types/aiReport";
import type { FrameReport } from "../types/frameReport";

export function generateAIReport(
  stats: FrameReport,
  context: { location_label?: string; scene_tags?: string[] } = {}
) {
  return requestJson<AIReportResult>("/api/ai/report", {
    method: "POST",
    body: JSON.stringify({ stats, ...context })
  });
}
