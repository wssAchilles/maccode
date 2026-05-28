export interface AIReportResult {
  provider: string;
  report_markdown: string;
  input_summary: {
    frame_index: number;
    active_tracks: number;
    total_in: number;
    total_out: number;
    avg_speed_kmh: number | null;
    calibration_quality?: string | null;
    traffic_flow?: Record<string, unknown> | null;
    zones: string[];
  };
  dynamic_context: {
    scene: {
      location_label: string;
      scene_tags: string[];
    };
    physical_state: Record<string, unknown>;
    motion_routes: Array<Record<string, unknown>>;
    risk_signals: Array<Record<string, unknown>>;
    decision_constraints: string[];
  };
}
