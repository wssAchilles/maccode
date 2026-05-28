import { requestJson } from "./client";
import type { CumulativeStats, FrameReport } from "../types/frameReport";

export function getRealtimeStats() {
  return requestJson<FrameReport>("/api/stats/realtime");
}

export function getHistoryStats(limit = 100) {
  return requestJson<FrameReport[]>(`/api/stats/history?limit=${limit}`);
}

export function getCumulativeStats() {
  return requestJson<CumulativeStats>("/api/stats/cumulative");
}
