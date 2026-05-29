import { useEffect, useRef } from "react";

import type { HomographyGrid, SafetyMetrics, Track } from "../../types/frameReport";
import { formatDegrees, formatSpeed, formatSpeedInterval } from "../../utils/formatters";

interface VideoPanelProps {
  tracks: Track[];
  homographyGrid?: HomographyGrid | null;
  renderedByBackend?: boolean;
  safetyMetrics?: SafetyMetrics | null;
  videoUrl?: string | null;
  calibrationQuality?: string | null;
}

interface ViewBox {
  width: number;
  height: number;
}

const DEFAULT_VIEW_BOX = { width: 1280, height: 720 };

function usesSyntheticScale(tracks: Track[]) {
  const maxX = Math.max(...tracks.flatMap((track) => [track.xyxy[0], track.xyxy[2]]), 0);
  const maxY = Math.max(...tracks.flatMap((track) => [track.xyxy[1], track.xyxy[3]]), 0);
  return maxX <= 120 && maxY <= 80;
}

function scaleBox(track: Track, syntheticScale: boolean): [number, number, number, number] {
  if (!syntheticScale) {
    return track.xyxy;
  }
  const [x1, y1, x2, y2] = track.xyxy;
  return [x1 * 12.8, y1 * 12, x2 * 12.8, y2 * 12];
}

function classTone(track: Track, safetyMetrics: SafetyMetrics | null | undefined) {
  if (safetyMetrics?.red_light_violation_track_ids?.includes(track.tracker_id)) {
    return "violation";
  }
  if (safetyMetrics?.speeding_track_ids?.includes(track.tracker_id)) {
    return "danger";
  }
  if (track.class_id === 0) {
    return "person";
  }
  return "vehicle";
}

function trailPoints(track: Track, box: [number, number, number, number]) {
  const [x1, , x2, y2] = box;
  const centerX = (x1 + x2) / 2;
  const centerY = y2;
  const vx = track.velocity_x_mps ?? 0;
  const vy = track.velocity_y_mps ?? 0;
  return `${centerX - vx * 16},${centerY - vy * 16} ${centerX - vx * 8},${centerY - vy * 8} ${centerX},${centerY}`;
}

function useHomographyCanvas(grid: HomographyGrid | null | undefined) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }
    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }
    context.clearRect(0, 0, canvas.width, canvas.height);
    if (!grid) {
      return;
    }
    context.save();
    context.globalAlpha = 0.32;
    context.strokeStyle = "#cbd5e1";
    context.lineWidth = 2;
    context.setLineDash([8, 10]);
    for (const line of grid.lines) {
      context.beginPath();
      context.moveTo(line.pixel_start[0], line.pixel_start[1]);
      context.lineTo(line.pixel_end[0], line.pixel_end[1]);
      context.stroke();
    }
    context.restore();
  }, [grid]);

  return canvasRef;
}

export function VideoPanel({
  tracks,
  homographyGrid,
  renderedByBackend = false,
  safetyMetrics,
  videoUrl,
  calibrationQuality
}: VideoPanelProps) {
  const viewBox = homographyGrid
    ? { width: homographyGrid.frame_width, height: homographyGrid.frame_height }
    : DEFAULT_VIEW_BOX;
  const syntheticScale = !homographyGrid && usesSyntheticScale(tracks);
  const canvasRef = useHomographyCanvas(homographyGrid);
  const showHomographyGrid = Boolean(videoUrl && homographyGrid);
  const showClientTrackOverlay = Boolean(videoUrl) && !renderedByBackend;
  const showBackendBadge = Boolean(videoUrl) && renderedByBackend;

  return (
    <section className="video-surface">
      {videoUrl ? (
        <video
          autoPlay={renderedByBackend}
          className="analysis-video"
          controls
          loop={renderedByBackend}
          muted
          playsInline
          src={videoUrl}
        />
      ) : (
        <div className="video-placeholder">
          <span>请选择 MP4 并开始真实分析</span>
        </div>
      )}
      {showHomographyGrid && (
        <canvas
          aria-label="homography grid projected from backend calibration"
          className="homography-canvas"
          height={viewBox.height}
          ref={canvasRef}
          width={viewBox.width}
        />
      )}
      {showClientTrackOverlay && (
        <>
          <svg
            aria-label="traffic perception overlay"
            className="video-overlay"
            preserveAspectRatio="none"
            viewBox={`0 0 ${viewBox.width} ${viewBox.height}`}
          >
            {tracks.map((track) => {
              const [x1, y1, x2, y2] = scaleBox(track, syntheticScale);
              const tone = classTone(track, safetyMetrics);
              const labelX = x1;
              const labelY = Math.max(18, y1 - 10);
              return (
                <g className={`track-overlay ${tone}`} key={track.tracker_id}>
                  <polyline
                    className="track-trail"
                    points={trailPoints(track, [x1, y1, x2, y2])}
                  />
                  <rect height={y2 - y1} rx="6" width={x2 - x1} x={x1} y={y1} />
                  <foreignObject height="54" width="190" x={labelX} y={labelY - 50}>
                    <div className="track-label">
                      <strong>{`#${track.tracker_id} ${track.class_name}`}</strong>
                      <span>{formatSpeed(track.speed_kmh)}</span>
                      {tone === "danger" && <small>speeding</small>}
                      {tone === "violation" && <small>red-light violation</small>}
                      <small>{formatSpeedInterval(track.speed_confidence_interval_kmh)}</small>
                      <small>{formatDegrees(track.heading_deg)}</small>
                    </div>
                  </foreignObject>
                </g>
              );
            })}
          </svg>
        </>
      )}
      {showBackendBadge && (
        <div className="overlay-badge">
          <strong>Homography Grid</strong>
          <span>{`Calibration ${calibrationQuality ?? "N/A"}`}</span>
          <small>backend_rendered_processed_mp4</small>
        </div>
      )}
    </section>
  );
}
