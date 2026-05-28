export interface AIReportResult {
  provider: string;
  report_markdown: string;
  input_summary: {
    frame_index: number;
    active_tracks: number;
    total_in: number;
    total_out: number;
    avg_speed_kmh: number | null;
    zones: string[];
  };
}
