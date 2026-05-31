import { useEffect, useRef, type SyntheticEvent } from "react";

import type { HomographyGrid, SafetyMetrics, Track } from "../../types/frameReport";
import { formatDegrees, formatSpeedInterval, formatValidatedSpeed } from "../../utils/formatters";

interface VideoPanelProps {
  tracks: Track[];
  homographyGrid?: HomographyGrid | null;
  renderedByBackend?: boolean;
  safetyMetrics?: SafetyMetrics | null;
  videoUrl?: string | null;
  calibrationQuality?: string | null;
  onPlaybackSnapshot?: (snapshot: VideoPlaybackSnapshot) => void;
}

interface ViewBox {
  width: number;
  height: number;
}

export interface VideoPlaybackSnapshot {
  currentTimeSec: number;
  durationSec: number;
  isPlaying: boolean;
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

function qualityText(track: Track) {
  if (track.physics_valid) {
    return null;
  }
  if (track.quality_label === "warming_up") {
    return "warming up";
  }
  if (track.quality_label === "rejected") {
    return "physics rejected";
  }
  if (track.quality_label === "low_confidence") {
    return "low confidence";
  }
  return track.quality_label;
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
    if (!grid?.calibration_trusted) {
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
  calibrationQuality,
  onPlaybackSnapshot
}: VideoPanelProps) {
  const viewBox = homographyGrid
    ? { width: homographyGrid.frame_width, height: homographyGrid.frame_height }
    : DEFAULT_VIEW_BOX;
  const syntheticScale = !homographyGrid && usesSyntheticScale(tracks);
  const canvasRef = useHomographyCanvas(homographyGrid);
  const showHomographyGrid = Boolean(videoUrl && homographyGrid?.calibration_trusted);
  const showClientTrackOverlay = Boolean(videoUrl) && !renderedByBackend;
  const emitPlaybackSnapshot = (event: SyntheticEvent<HTMLVideoElement>, isPlaying?: boolean) => {
    const video = event.currentTarget;
    onPlaybackSnapshot?.({
      currentTimeSec: video.currentTime,
      durationSec: Number.isFinite(video.duration) ? video.duration : 0,
      isPlaying: isPlaying ?? !video.paused
    });
  };

  return (
    <section className="video-surface">
      {videoUrl ? (
        <video
          autoPlay
          className="analysis-video"
          controls
          loop={renderedByBackend}
          muted
          onLoadedMetadata={(event) => emitPlaybackSnapshot(event, !event.currentTarget.paused)}
          onPause={(event) => emitPlaybackSnapshot(event, false)}
          onPlay={(event) => emitPlaybackSnapshot(event, true)}
          onTimeUpdate={(event) => emitPlaybackSnapshot(event)}
          playsInline
          src={videoUrl}
        />
      ) : (
        <div className="video-placeholder" aria-label="video signal standby">
          <div className="video-scanner">
            <span />
            <span />
            <span />
          </div>
          <div className="video-placeholder-copy">
            <strong>视频信号待接入</strong>
            <span>CV Pipeline Standby</span>
          </div>
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
                      <span>
                        {formatValidatedSpeed(
                          track.speed_kmh,
                          track.physics_valid,
                          track.quality_label
                        )}
                      </span>
                      {tone === "danger" && <small>speeding</small>}
                      {tone === "violation" && <small>red-light violation</small>}
                      {qualityText(track) && <small>{qualityText(track)}</small>}
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
    </section>
  );
}
