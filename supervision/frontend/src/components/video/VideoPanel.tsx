import type { Track } from "../../types/frameReport";
import { formatDegrees, formatSpeed, formatSpeedInterval } from "../../utils/formatters";

interface VideoPanelProps {
  tracks: Track[];
}

export function VideoPanel({ tracks }: VideoPanelProps) {
  return (
    <section className="video-surface">
      <div className="road-lane" />
      {tracks.map((track) => (
        <div className="tracked-object" key={track.tracker_id}>
          <strong>#{track.tracker_id}</strong>
          <span>{formatSpeed(track.speed_kmh)}</span>
          <small>{formatSpeedInterval(track.speed_confidence_interval_kmh)}</small>
          <small>{formatDegrees(track.heading_deg)}</small>
        </div>
      ))}
    </section>
  );
}
