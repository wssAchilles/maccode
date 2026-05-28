import type { Track } from "../../types/frameReport";

interface VideoPanelProps {
  tracks: Track[];
}

export function VideoPanel({ tracks }: VideoPanelProps) {
  return (
    <section className="video-surface">
      <div className="road-lane" />
      {tracks.map((track) => (
        <div className="tracked-object" key={track.tracker_id}>
          <span>#{track.tracker_id}</span>
        </div>
      ))}
    </section>
  );
}
