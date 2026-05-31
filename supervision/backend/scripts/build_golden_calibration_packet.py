# ruff: noqa: E501

from __future__ import annotations

import argparse
import html
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/mpl")

import cv2

from scripts.analyze_real_videos import inspect_video
from scripts.build_calibration_qa import (
    GOLDEN_CLIPS,
    build_qa_summary,
    read_video_frame,
)

SAMPLING_GUIDES = {
    "026_complex_signal_day_wide_0115s_30s.mp4": [
        "Pick 6-10 points on the same road plane.",
        "Prefer lane-marking corners, stop-line edges, crosswalk edges, and curb-road joins.",
        "Avoid traffic lights, poles, vehicle roofs, trees, building edges, and shadows.",
        "Use X across road width and Y along traffic direction.",
        "Validation segments must be lane/stop/crosswalk edges not reused as fit evidence.",
    ],
    "042_pedestrian_crowd_high_view_0270s_30s.mp4": [
        "Pick pavement tile corners, corridor edge intersections, curb seams, or ground marks.",
        "Avoid heads, shoulders, shop facades, benches, signs, and vertical objects.",
        "Use X across corridor width and Y along pedestrian flow direction.",
        "Validate with long pavement-edge or tile-grid lines separate from control points.",
    ],
    "054_dense_city_traffic_4k_elevated_0030s_30s.mp4": [
        "Pick lane-marking intersections and road-edge points on the visible roadway.",
        "Spread points from near to far field; do not cluster at the bottom of the 4K frame.",
        "Use X across total roadway width and Y along the corridor direction.",
        "Validate with an independent lane bundle or road-edge segment.",
    ],
    "058_dense_city_traffic_4k_elevated_0150s_30s.mp4": [
        "Reuse the 054 camera profile only if visual alignment is identical.",
        "Otherwise calibrate separately as a distinct fixed camera profile.",
        "Pick the same physical lane/road-edge landmarks as 054 where visible.",
        "Use X across total roadway width and Y along the corridor direction.",
        "If validation differs strongly from 054, treat it as a distinct camera profile.",
    ],
}

OPERATOR_CHECKLIST = [
    "Pause on the clearest frame before sampling; prefer visible lane/crosswalk/pavement geometry.",
    "Collect 8-10 same-ground-plane manual_control_points per fixed camera.",
    "Use meters for world coordinates; record the scale prior that anchors the scene.",
    "Add at least 2 independent validation_segments that were not reused as fitting evidence.",
    "Keep calibration_trusted=false until validation_max_error_px is below 15 px.",
    "Promote to camera_manual_preset only after the video_manual_preset passes the audit.",
]

WORLD_COORDINATE_PROTOCOL = [
    "Set X across the road/corridor width and Y along the dominant movement direction.",
    "Put (0, 0) on a near visible ground-plane corner that can be re-identified later.",
    "Use traffic priors only when direct survey data is unavailable, and record the prior.",
    "Typical priors: lane width 3.5 m, crosswalk width 3-4 m, pavement tiles from visible repeats.",
    "Do not mix road surface with sidewalks/building facades if they are not coplanar.",
]

PROFILE_METADATA_TEMPLATES = {
    "026_complex_signal_day_wide_0115s_30s.mp4": {
        "world_width_m": 28.0,
        "world_length_m": 75.0,
        "position_rmse_floor_m": 1.3,
        "calibration_scale_uncertainty_pct": 6.0,
        "scale_prior_kind": "traffic_standard_or_survey",
        "scale_prior_description": "REPLACE_WITH_SURVEY_OR_LANE_WIDTH_PRIOR",
        "profile_notes": "REPLACE_WITH_FIXED_CAMERA_AND_COPLANAR_POINT_NOTES",
    },
    "042_pedestrian_crowd_high_view_0270s_30s.mp4": {
        "world_width_m": 22.0,
        "world_length_m": 45.0,
        "position_rmse_floor_m": 1.0,
        "calibration_scale_uncertainty_pct": 5.0,
        "scale_prior_kind": "traffic_standard_or_survey",
        "scale_prior_description": "REPLACE_WITH_SURVEY_OR_PAVEMENT_WIDTH_PRIOR",
        "profile_notes": "REPLACE_WITH_FIXED_CAMERA_AND_COPLANAR_POINT_NOTES",
    },
    "054_dense_city_traffic_4k_elevated_0030s_30s.mp4": {
        "world_width_m": 38.0,
        "world_length_m": 110.0,
        "position_rmse_floor_m": 2.0,
        "calibration_scale_uncertainty_pct": 10.0,
        "scale_prior_kind": "traffic_standard_or_survey",
        "scale_prior_description": "REPLACE_WITH_SURVEY_OR_MULTI_LANE_WIDTH_PRIOR",
        "profile_notes": "REPLACE_WITH_FIXED_CAMERA_AND_COPLANAR_POINT_NOTES",
    },
    "058_dense_city_traffic_4k_elevated_0150s_30s.mp4": {
        "world_width_m": 38.0,
        "world_length_m": 110.0,
        "position_rmse_floor_m": 2.0,
        "calibration_scale_uncertainty_pct": 10.0,
        "scale_prior_kind": "traffic_standard_or_survey",
        "scale_prior_description": "REPLACE_WITH_SURVEY_OR_MULTI_LANE_WIDTH_PRIOR",
        "profile_notes": "REPLACE_WITH_FIXED_CAMERA_AND_COPLANAR_POINT_NOTES",
    },
}

DEFAULT_PROFILE_METADATA = {
    "annotation_method": "manual_ground_control_point_picker",
    "evidence_sources": [
        "manual_pixel_clicks_on_exported_keyframe",
        "measured_or_declared_meter_scale_anchor",
    ],
}


def draw_pixel_coordinate_guide(frame: Any, step: int) -> Any:
    guide = frame.copy()
    height, width = guide.shape[:2]
    overlay = guide.copy()
    for x in range(0, width + 1, step):
        cv2.line(overlay, (x, 0), (x, height), (80, 160, 255), 1, cv2.LINE_AA)
        cv2.putText(
            overlay,
            str(x),
            (min(x + 6, max(width - 70, 0)), 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (235, 245, 255),
            2,
            cv2.LINE_AA,
        )
    for y in range(0, height + 1, step):
        cv2.line(overlay, (0, y), (width, y), (80, 160, 255), 1, cv2.LINE_AA)
        cv2.putText(
            overlay,
            str(y),
            (10, min(y + 24, max(height - 10, 0))),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (235, 245, 255),
            2,
            cv2.LINE_AA,
        )
    cv2.addWeighted(overlay, 0.38, guide, 0.62, 0, dst=guide)
    cv2.rectangle(guide, (14, height - 68), (min(width - 14, 760), height - 16), (5, 10, 22), -1)
    cv2.putText(
        guide,
        "Pixel coordinate guide: click true ground-plane landmarks only",
        (28, height - 34),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.78,
        (245, 248, 255),
        2,
        cv2.LINE_AA,
    )
    return guide


def draw_line_candidate_guide(frame: Any) -> Any:
    guide = frame.copy()
    gray = cv2.cvtColor(guide, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 60, 160, apertureSize=3)
    min_length = max(50, min(frame.shape[:2]) // 8)
    raw_lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=3.141592653589793 / 180,
        threshold=80,
        minLineLength=min_length,
        maxLineGap=18,
    )
    if raw_lines is None:
        return guide

    candidates: list[tuple[float, tuple[int, int, int, int]]] = []
    for line in raw_lines[:, 0, :]:
        x1, y1, x2, y2 = (int(value) for value in line)
        length = float(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5)
        if length < min_length:
            continue
        # Prefer lower-image ground evidence over skyline/building edges.
        ground_weight = 0.4 + 0.6 * max(y1, y2) / max(frame.shape[0], 1)
        candidates.append((length * ground_weight, (x1, y1, x2, y2)))

    candidates.sort(reverse=True, key=lambda item: item[0])
    overlay = guide.copy()
    for index, (_, (x1, y1, x2, y2)) in enumerate(candidates[:36], start=1):
        color = (40, 220, 255) if index <= 18 else (80, 160, 255)
        cv2.line(overlay, (x1, y1), (x2, y2), color, 3, cv2.LINE_AA)
        midpoint = (int(round((x1 + x2) / 2)), int(round((y1 + y2) / 2)))
        cv2.circle(overlay, midpoint, 10, (4, 10, 20), -1, cv2.LINE_AA)
        cv2.putText(
            overlay,
            str(index),
            (midpoint[0] - 7, midpoint[1] + 6),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (245, 248, 255),
            2,
            cv2.LINE_AA,
        )
    cv2.addWeighted(overlay, 0.58, guide, 0.42, 0, dst=guide)
    cv2.rectangle(guide, (14, 14), (min(frame.shape[1] - 14, 860), 72), (5, 10, 22), -1)
    cv2.putText(
        guide,
        "Candidate ground-line guide: verify manually before using as control/validation evidence",
        (28, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (245, 248, 255),
        2,
        cv2.LINE_AA,
    )
    return guide


def write_image(path: Path, frame: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), frame):
        raise ValueError(f"could not write image: {path}")


def candidate_frame_indexes(metadata: dict[str, Any], requested_frame: int) -> list[int]:
    frame_count = int(metadata.get("frame_count") or 0)
    if frame_count <= 1:
        return [0]
    max_index = frame_count - 1
    candidates = [
        requested_frame,
        int(max_index * 0.25),
        int(max_index * 0.50),
        int(max_index * 0.75),
    ]
    return sorted({min(max(index, 0), max_index) for index in candidates})


def render_sampling_template(clip: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"{clip['clip']}:",
            "  source: video_manual_preset",
            "  calibration_trusted: false",
            "  scale_prior:",
            "    kind: traffic_standard_or_survey",
            "    description: TODO record lane/crosswalk/tile measurement used as meter anchor",
            "  profile_notes: TODO describe camera/profile and why points are coplanar",
            "  road_plane_polygon_pixel:",
            "    - [TODO, TODO]",
            "    - [TODO, TODO]",
            "    - [TODO, TODO]",
            "    - [TODO, TODO]",
            "  road_plane_polygon_world:",
            "    - [0.0, 0.0]",
            "    - [TODO_width_m, 0.0]",
            "    - [TODO_width_m, TODO_length_m]",
            "    - [0.0, TODO_length_m]",
            "  validation_segments:",
            "    - name: TODO_independent_road_marking_1",
            "      pixel_start: [TODO, TODO]",
            "      pixel_end: [TODO, TODO]",
            "      world_start: [TODO, TODO]",
            "      world_end: [TODO, TODO]",
            "    - name: TODO_independent_road_marking_2",
            "      pixel_start: [TODO, TODO]",
            "      pixel_end: [TODO, TODO]",
            "      world_start: [TODO, TODO]",
            "      world_end: [TODO, TODO]",
            "  points:",
            "    - {pixel_x: TODO, pixel_y: TODO, world_x: TODO, world_y: TODO}",
            "    - {pixel_x: TODO, pixel_y: TODO, world_x: TODO, world_y: TODO}",
            "    - {pixel_x: TODO, pixel_y: TODO, world_x: TODO, world_y: TODO}",
            "    - {pixel_x: TODO, pixel_y: TODO, world_x: TODO, world_y: TODO}",
            "    - {pixel_x: TODO, pixel_y: TODO, world_x: TODO, world_y: TODO}",
            "    - {pixel_x: TODO, pixel_y: TODO, world_x: TODO, world_y: TODO}",
            "    - {pixel_x: TODO, pixel_y: TODO, world_x: TODO, world_y: TODO}",
            "    - {pixel_x: TODO, pixel_y: TODO, world_x: TODO, world_y: TODO}",
        ],
    )


def build_profile_metadata_template(clips: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    metadata: dict[str, dict[str, Any]] = {}
    for clip in clips:
        template = PROFILE_METADATA_TEMPLATES.get(
            clip["clip"],
            {
                "world_width_m": "REPLACE_WITH_WIDTH_M",
                "world_length_m": "REPLACE_WITH_LENGTH_M",
                "position_rmse_floor_m": 1.0,
                "calibration_scale_uncertainty_pct": 5.0,
                "scale_prior_kind": "traffic_standard_or_survey",
                "scale_prior_description": "REPLACE_WITH_REAL_SCALE_PRIOR",
                "profile_notes": "REPLACE_WITH_FIXED_CAMERA_AND_COPLANAR_POINT_NOTES",
            },
        )
        metadata[clip["clip"]] = {**DEFAULT_PROFILE_METADATA, **template}
    return metadata


def build_manual_picks_template(clips: list[dict[str, Any]]) -> dict[str, Any]:
    metadata = build_profile_metadata_template(clips)
    payload: dict[str, Any] = {"__profile_metadata__": metadata}
    for clip in clips:
        clip_name = clip["clip"]
        profile = metadata[clip_name]
        payload[clip_name] = {
            "annotation_method": profile["annotation_method"],
            "evidence_sources": profile["evidence_sources"],
            "scale_prior": {
                "kind": profile["scale_prior_kind"],
                "description": profile["scale_prior_description"],
            },
            "control_points": [],
            "validation_segments": [],
            "road_plane_polygon_pixel": [],
        }
    return payload


def render_picker_html(manifest: dict[str, Any]) -> str:
    payload = {
        "clips": [
            {
                "clip": clip["clip"],
                "width": clip["metadata"]["width"],
                "height": clip["metadata"]["height"],
                "frames": [
                    os.path.relpath(path, manifest["output_dir"])
                    for path in clip["candidate_frames"]
                ],
                "guide": os.path.relpath(clip["coordinate_guide"], manifest["output_dir"]),
            }
            for clip in manifest["clips"]
        ],
        "operatorChecklist": manifest["operator_checklist"],
        "worldCoordinateProtocol": manifest["world_coordinate_protocol"],
        "profileMetadataTemplates": build_profile_metadata_template(manifest["clips"]),
    }
    data_json = html.escape(json.dumps(payload, ensure_ascii=False), quote=False)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Golden Calibration Picker</title>
  <style>
    :root {{
      color-scheme: dark;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
      background: #07101f;
      color: #e8eefc;
    }}
    body {{ margin: 0; }}
    main {{ display: grid; grid-template-columns: minmax(0, 1fr) 420px; gap: 18px; padding: 18px; }}
    .panel {{ background: #0d1526; border: 1px solid #254064; border-radius: 8px; padding: 14px; }}
    .toolbar {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin-bottom: 12px; }}
    .metadata {{ display: grid; gap: 10px; margin: 12px 0; }}
    label {{ display: grid; gap: 6px; color: #9fb5d6; font-size: 13px; }}
    select, input, textarea, button {{
      background: #091223; color: #f7faff; border: 1px solid #2b4975; border-radius: 6px;
      min-height: 36px; padding: 8px 10px; font: inherit;
    }}
    button {{ cursor: pointer; background: #1d4ed8; border-color: #3b82f6; font-weight: 700; }}
    button.secondary {{ background: #111b2e; }}
    .canvas-wrap {{ overflow: auto; max-height: calc(100vh - 150px); border-radius: 8px; background: #020617; }}
    canvas {{ display: block; max-width: 100%; height: auto; }}
    textarea {{ width: 100%; min-height: 260px; resize: vertical; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
    .hint {{ color: #b7c8e6; line-height: 1.5; }}
    .small {{ font-size: 12px; color: #93a8c9; }}
  </style>
</head>
<body>
<main>
  <section class="panel">
    <div class="toolbar">
      <label>Clip<select id="clip"></select></label>
      <label>Frame<select id="frame"></select></label>
      <label>Mode
        <select id="mode">
          <option value="point">control point</option>
          <option value="segment">validation segment</option>
          <option value="polygon">road polygon pixel</option>
        </select>
      </label>
      <label>World X/Y for next click<input id="world" value="0,0" /></label>
    </div>
    <div class="toolbar">
      <label>Validation world start<input id="segmentStart" value="0,0" /></label>
      <label>Validation world end<input id="segmentEnd" value="3.5,0" /></label>
    </div>
    <div class="canvas-wrap"><canvas id="canvas"></canvas></div>
  </section>
  <aside class="panel">
    <h1>Golden Calibration Picker</h1>
    <p class="hint">Click true ground-plane landmarks only. This helper records pixel coordinates; meters still require a real survey or explicit traffic prior.</p>
    <p class="small">Recommended: 8-10 control points, at least 2 independent validation segments, and a road polygon that bounds only the ground plane.</p>
    <div class="metadata">
      <label>World width / length (m)<input id="worldSize" value="0,0" /></label>
      <label>Evidence sources<textarea id="evidenceSources" spellcheck="false"></textarea></label>
      <label>Scale prior description<textarea id="scalePrior" spellcheck="false"></textarea></label>
      <label>Profile notes<textarea id="profileNotes" spellcheck="false"></textarea></label>
    </div>
    <div class="toolbar">
      <button id="undo" class="secondary">Undo</button>
      <button id="clear" class="secondary">Clear clip</button>
      <button id="copy">Copy YAML</button>
      <button id="download" class="secondary">Download JSON</button>
    </div>
    <textarea id="yaml" spellcheck="false"></textarea>
  </aside>
</main>
<script id="packet-data" type="application/json">{data_json}</script>
<script>
const packet = JSON.parse(document.getElementById("packet-data").textContent);
const state = new Map();
const clipSelect = document.getElementById("clip");
const frameSelect = document.getElementById("frame");
const modeSelect = document.getElementById("mode");
const worldInput = document.getElementById("world");
const segmentStartInput = document.getElementById("segmentStart");
const segmentEndInput = document.getElementById("segmentEnd");
const worldSizeInput = document.getElementById("worldSize");
const evidenceSourcesInput = document.getElementById("evidenceSources");
const scalePriorInput = document.getElementById("scalePrior");
const profileNotesInput = document.getElementById("profileNotes");
const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");
const image = new Image();
let pendingSegment = null;

function pointText(point) {{
  return `[${{point[0].toFixed(2)}}, ${{point[1].toFixed(2)}}]`;
}}
function parsePair(value) {{
  const parts = value.split(",").map((part) => Number(part.trim()));
  return [parts[0] || 0, parts[1] || 0];
}}
function clipState(name) {{
  if (!state.has(name)) {{
    const template = JSON.parse(JSON.stringify(packet.profileMetadataTemplates[name] || {{}}));
    state.set(name, {{ points: [], segments: [], polygon: [], metadata: template }});
  }}
  return state.get(name);
}}
function selectedClip() {{
  return packet.clips.find((clip) => clip.clip === clipSelect.value);
}}
function syncMetadataInputs() {{
  const current = clipState(clipSelect.value);
  const metadata = current.metadata || {{}};
  worldSizeInput.value = `${{metadata.world_width_m || 0}},${{metadata.world_length_m || 0}}`;
  evidenceSourcesInput.value = (metadata.evidence_sources || []).join("\\n");
  scalePriorInput.value = metadata.scale_prior_description || "";
  profileNotesInput.value = metadata.profile_notes || "";
}}
function updateMetadataFromInputs() {{
  const current = clipState(clipSelect.value);
  const size = parsePair(worldSizeInput.value);
  current.metadata = {{
    ...(current.metadata || {{}}),
    annotation_method: "manual_ground_control_point_picker",
    evidence_sources: evidenceSourcesInput.value
      .split("\\n")
      .map((item) => item.trim())
      .filter(Boolean),
    world_width_m: size[0],
    world_length_m: size[1],
    scale_prior_kind: "traffic_standard_or_survey",
    scale_prior_description: scalePriorInput.value.trim(),
    profile_notes: profileNotesInput.value.trim(),
  }};
}}
function redraw() {{
  const clip = selectedClip();
  if (!clip || !image.complete) return;
  canvas.width = clip.width;
  canvas.height = clip.height;
  ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
  const current = clipState(clip.clip);
  ctx.lineWidth = 3;
  current.polygon.forEach((point, index) => {{
    ctx.fillStyle = "#facc15";
    ctx.beginPath(); ctx.arc(point[0], point[1], 7, 0, Math.PI * 2); ctx.fill();
    if (index > 0) {{
      const prev = current.polygon[index - 1];
      ctx.strokeStyle = "#facc15"; ctx.beginPath(); ctx.moveTo(prev[0], prev[1]); ctx.lineTo(point[0], point[1]); ctx.stroke();
    }}
  }});
  current.points.forEach((point, index) => {{
    ctx.fillStyle = "#22c55e";
    ctx.beginPath(); ctx.arc(point.pixel[0], point.pixel[1], 6, 0, Math.PI * 2); ctx.fill();
    ctx.fillText(`P${{index + 1}}`, point.pixel[0] + 8, point.pixel[1] - 8);
  }});
  current.segments.forEach((segment, index) => {{
    ctx.strokeStyle = "#60a5fa"; ctx.beginPath(); ctx.moveTo(segment.pixel_start[0], segment.pixel_start[1]); ctx.lineTo(segment.pixel_end[0], segment.pixel_end[1]); ctx.stroke();
    ctx.fillStyle = "#bfdbfe"; ctx.fillText(`V${{index + 1}}`, segment.pixel_start[0] + 8, segment.pixel_start[1] - 8);
  }});
}}
function renderYaml() {{
  const clip = selectedClip();
  const current = clipState(clip.clip);
  updateMetadataFromInputs();
  const metadata = current.metadata || {{}};
  const lines = [
    `${{clip.clip}}:`,
    "  source: video_manual_preset",
    "  calibration_trusted: false",
    "  scale_prior:",
    "    kind: traffic_standard_or_survey",
    `    description: "${{metadata.scale_prior_description || "TODO record lane/crosswalk/tile measurement used as meter anchor"}}"`,
    `  profile_notes: "${{metadata.profile_notes || "TODO describe camera/profile and why points are coplanar"}}"`,
    "  road_plane_polygon_pixel:",
    ...current.polygon.map((point) => `    - ${{pointText(point)}}`),
    "  road_plane_polygon_world:",
    "    - [0.0, 0.0]",
    `    - [${{metadata.world_width_m || "TODO_width_m"}}, 0.0]`,
    `    - [${{metadata.world_width_m || "TODO_width_m"}}, ${{metadata.world_length_m || "TODO_length_m"}}]`,
    `    - [0.0, ${{metadata.world_length_m || "TODO_length_m"}}]`,
    "  validation_segments:",
    ...current.segments.flatMap((segment, index) => [
      `    - name: independent_segment_${{index + 1}}`,
      `      pixel_start: ${{pointText(segment.pixel_start)}}`,
      `      pixel_end: ${{pointText(segment.pixel_end)}}`,
      `      world_start: ${{pointText(segment.world_start)}}`,
      `      world_end: ${{pointText(segment.world_end)}}`,
    ]),
    "  points:",
    ...current.points.map((point) => `    - {{pixel_x: ${{point.pixel[0].toFixed(2)}}, pixel_y: ${{point.pixel[1].toFixed(2)}}, world_x: ${{point.world[0]}}, world_y: ${{point.world[1]}}}}`),
  ];
  document.getElementById("yaml").value = lines.join("\\n");
}}
function loadFrame() {{
  const clip = selectedClip();
  image.onload = () => {{ redraw(); renderYaml(); }};
  image.src = frameSelect.value;
}}
packet.clips.forEach((clip) => {{
  clipState(clip.clip);
  const option = document.createElement("option");
  option.value = clip.clip; option.textContent = clip.clip; clipSelect.appendChild(option);
}});
function refreshFrames() {{
  const clip = selectedClip();
  syncMetadataInputs();
  frameSelect.innerHTML = "";
  clip.frames.forEach((frame) => {{
    const option = document.createElement("option");
    option.value = frame; option.textContent = frame.split("/").pop(); frameSelect.appendChild(option);
  }});
  loadFrame();
}}
clipSelect.addEventListener("change", refreshFrames);
frameSelect.addEventListener("change", loadFrame);
canvas.addEventListener("click", (event) => {{
  const rect = canvas.getBoundingClientRect();
  const pixel = [
    (event.clientX - rect.left) * (canvas.width / rect.width),
    (event.clientY - rect.top) * (canvas.height / rect.height),
  ];
  const current = clipState(clipSelect.value);
  if (modeSelect.value === "point") current.points.push({{ pixel, world: parsePair(worldInput.value) }});
  if (modeSelect.value === "polygon") current.polygon.push(pixel);
  if (modeSelect.value === "segment") {{
    if (!pendingSegment) pendingSegment = pixel;
    else {{
      current.segments.push({{
        pixel_start: pendingSegment,
        pixel_end: pixel,
        world_start: parsePair(segmentStartInput.value),
        world_end: parsePair(segmentEndInput.value),
      }});
      pendingSegment = null;
    }}
  }}
  redraw(); renderYaml();
}});
worldSizeInput.addEventListener("input", renderYaml);
scalePriorInput.addEventListener("input", renderYaml);
evidenceSourcesInput.addEventListener("input", renderYaml);
profileNotesInput.addEventListener("input", renderYaml);
document.getElementById("undo").addEventListener("click", () => {{
  const current = clipState(clipSelect.value);
  if (modeSelect.value === "point") current.points.pop();
  if (modeSelect.value === "polygon") current.polygon.pop();
  if (modeSelect.value === "segment") current.segments.pop();
  pendingSegment = null; redraw(); renderYaml();
}});
document.getElementById("clear").addEventListener("click", () => {{
  const current = clipState(clipSelect.value);
  state.set(clipSelect.value, {{ points: [], segments: [], polygon: [], metadata: current.metadata || {{}} }});
  pendingSegment = null; redraw(); renderYaml();
}});
document.getElementById("copy").addEventListener("click", async () => {{
  await navigator.clipboard.writeText(document.getElementById("yaml").value);
}});
document.getElementById("download").addEventListener("click", () => {{
  updateMetadataFromInputs();
  const payload = {{}};
  const profileMetadata = {{}};
  for (const [clip, current] of state.entries()) {{
    const metadata = current.metadata || {{}};
    payload[clip] = {{
      annotation_method: metadata.annotation_method || "manual_ground_control_point_picker",
      evidence_sources: metadata.evidence_sources || [],
      scale_prior: {{
        kind: metadata.scale_prior_kind || "traffic_standard_or_survey",
        description: metadata.scale_prior_description || "",
      }},
      control_points: current.points,
      validation_segments: current.segments,
      road_plane_polygon_pixel: current.polygon,
    }};
    profileMetadata[clip] = metadata;
  }}
  payload.__profile_metadata__ = profileMetadata;
  const blob = new Blob([JSON.stringify(payload, null, 2)], {{ type: "application/json" }});
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob); link.download = "golden-calibration-picks.json"; link.click();
  URL.revokeObjectURL(link.href);
}});
refreshFrames();
</script>
</body>
</html>
"""


def render_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# Golden Calibration Packet",
        "",
        "Purpose: collect real ground-plane control points for the four golden clips.",
        (
            "Only clips with manual/survey provenance and independent validation error "
            "below 15 px may render Homography Grid."
        ),
        "",
        f"- Output dir: `{manifest['output_dir']}`",
        f"- Frame index: `{manifest['frame_index']}`",
        f"- Interactive picker: `{Path(manifest['picker_html']).name}`",
        f"- Profile metadata template: `{Path(manifest['profile_metadata_template']).name}`",
        f"- Manual picks template: `{Path(manifest['manual_picks_template']).name}`",
        (
            f"- QA trusted count: `{manifest['qa_summary']['trusted_count']}/"
            f"{manifest['qa_summary']['clip_count']}`"
        ),
        "",
        "| Clip | Resolution | Trusted | Validation max error | Keyframe | Coordinate guide | Line guide |",
        "| --- | ---: | --- | ---: | --- | --- | --- |",
    ]
    qa_by_clip = {row["clip"]: row for row in manifest["qa_summary"]["clips"]}
    for clip in manifest["clips"]:
        qa = qa_by_clip.get(clip["clip"], {})
        validation = qa.get("validation_max_error_px")
        validation_text = (
            "suppressed"
            if not qa.get("calibration_trusted", False)
            else "N/A"
            if validation is None
            else f"{validation:.2f}px"
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    clip["clip"],
                    f"{clip['metadata']['width']}x{clip['metadata']['height']}",
                    str(qa.get("calibration_trusted", False)),
                    validation_text,
                    Path(clip["keyframe"]).name,
                    Path(clip["coordinate_guide"]).name,
                    Path(clip["line_candidate_guide"]).name,
                ],
            )
            + " |",
        )
    lines.extend(["", "## Per-Clip Sampling Guide", ""])
    for clip in manifest["clips"]:
        lines.extend([f"### {clip['clip']}", ""])
        lines.append(f"- Keyframe: `{clip['keyframe']}`")
        lines.append(f"- Coordinate guide: `{clip['coordinate_guide']}`")
        lines.append(f"- Candidate ground-line guide: `{clip['line_candidate_guide']}`")
        lines.append(f"- Interactive picker: `{manifest['picker_html']}`")
        lines.append(f"- Profile metadata template: `{manifest['profile_metadata_template']}`")
        lines.append(f"- Manual picks template: `{manifest['manual_picks_template']}`")
        lines.append(
            "- Candidate frames: "
            + ", ".join(f"`{Path(path).name}`" for path in clip["candidate_frames"]),
        )
        lines.append(f"- Current QA image: `{clip['qa_image']}`")
        lines.append("- Recommended landmarks:")
        for item in clip["sampling_guide"]:
            lines.append(f"  - {item}")
        lines.append("- Operator checklist:")
        for item in OPERATOR_CHECKLIST:
            lines.append(f"  - {item}")
        lines.append("- World-coordinate protocol:")
        for item in WORLD_COORDINATE_PROTOCOL:
            lines.append(f"  - {item}")
        lines.extend(
            [
                "- Required YAML fields after sampling:",
                "  - `manual_control_points`: 6-10 true ground-plane pixel/world pairs",
                "  - `road_plane_polygon_pixel`: drawable ground area in frame pixels",
                "  - `road_plane_polygon_world`: drawable ground area in meters",
                "  - `validation_segments`: at least 2 independent line segments "
                "not reused as fit evidence",
                "- YAML starter block:",
                "```yaml",
                render_sampling_template(clip),
                "```",
                "",
            ],
        )
    lines.extend(
        [
            "## Acceptance Commands",
            "",
            "Run these after all four clips are sampled and saved:",
            "",
            "```bash",
            ".venv/bin/python backend/scripts/run_golden_calibration_acceptance.py",
            (
                ".venv/bin/python backend/scripts/merge_golden_calibration_picks.py "
                "~/Downloads/*.golden-calibration-picks.json "
                "--output data/outputs/golden_calibration_packet/golden-calibration-picks.json"
            ),
            (
                ".venv/bin/python backend/scripts/preflight_golden_calibration_picks.py "
                "--picks data/outputs/golden_calibration_packet/golden-calibration-picks.json "
                "--profile-metadata data/outputs/golden_calibration_packet/profile_metadata.yaml"
            ),
            (
                ".venv/bin/python backend/scripts/import_golden_calibration_picks.py "
                "--picks data/outputs/golden_calibration_packet/golden-calibration-picks.json "
                "--profile-metadata data/outputs/golden_calibration_packet/profile_metadata.yaml "
                "--trusted"
            ),
            ".venv/bin/python backend/scripts/promote_video_calibration_to_camera_profile.py",
            (
                ".venv/bin/python backend/scripts/run_golden_calibration_acceptance.py "
                "--run-analysis --strict"
            ),
            "```",
            "",
            "A clip is not defense-ready until the audit reports trusted calibration, "
            "at least 2 independent validation segments, validation error below 15 px, "
            "and grid_rendered=true from a manual camera/video preset.",
            "",
            "`import_golden_calibration_picks.py --trusted` refuses incomplete evidence: "
            "8+ control points, 2+ validation segment candidates, a pixel road polygon, "
            "a real scale_prior, and profile_notes are mandatory before the validation "
            "gate can even consider the clip trusted.",
            "",
        ],
    )
    return "\n".join(lines)


def build_packet(
    input_dir: Path,
    output_dir: Path,
    clips: list[str],
    frame_index: int,
    calibration_presets: Path,
    camera_profiles: Path,
    coordinate_step: int,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    qa_summary = build_qa_summary(
        input_dir=input_dir,
        output_dir=output_dir / "qa",
        calibration_presets=calibration_presets,
        camera_profiles=camera_profiles,
        clips=clips,
        frame_index=frame_index,
    )
    clip_rows = []
    for clip in clips:
        video_path = input_dir / clip
        metadata = inspect_video(video_path)
        frame_indexes = candidate_frame_indexes(metadata, frame_index)
        frame = read_video_frame(video_path, frame_indexes[0])
        keyframe_path = output_dir / "keyframes" / f"{video_path.stem}_frame_{frame_index}.jpg"
        guide_path = output_dir / "coordinate_guides" / f"{video_path.stem}_coordinates.jpg"
        line_guide_path = output_dir / "line_guides" / f"{video_path.stem}_line_candidates.jpg"
        write_image(keyframe_path, frame)
        write_image(guide_path, draw_pixel_coordinate_guide(frame, coordinate_step))
        write_image(line_guide_path, draw_line_candidate_guide(frame))
        candidate_paths = []
        for index in frame_indexes:
            candidate_frame = read_video_frame(video_path, index)
            candidate_path = (
                output_dir / "candidate_frames" / f"{video_path.stem}_frame_{index}.jpg"
            )
            write_image(candidate_path, candidate_frame)
            candidate_paths.append(str(candidate_path))
        qa_image = next(row["qa_image"] for row in qa_summary["clips"] if row["clip"] == clip)
        clip_rows.append(
            {
                "clip": clip,
                "metadata": metadata,
                "keyframe": str(keyframe_path),
                "coordinate_guide": str(guide_path),
                "line_candidate_guide": str(line_guide_path),
                "candidate_frame_indexes": frame_indexes,
                "candidate_frames": candidate_paths,
                "qa_image": qa_image,
                "sampling_guide": SAMPLING_GUIDES.get(
                    clip,
                    ["Pick 6-10 non-collinear true ground-plane landmarks."],
                ),
            },
        )
    manifest = {
        "output_dir": str(output_dir),
        "frame_index": frame_index,
        "coordinate_step_px": coordinate_step,
        "picker_html": str(output_dir / "golden_calibration_picker.html"),
        "profile_metadata_template": str(output_dir / "profile_metadata.yaml"),
        "manual_picks_template": str(output_dir / "manual-golden-calibration-picks.template.json"),
        "operator_checklist": OPERATOR_CHECKLIST,
        "world_coordinate_protocol": WORLD_COORDINATE_PROTOCOL,
        "qa_summary": qa_summary,
        "clips": clip_rows,
    }
    (output_dir / "golden_calibration_packet.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
    )
    (output_dir / "README.md").write_text(render_markdown(manifest))
    picker_path = Path(str(manifest["picker_html"]))
    picker_path.write_text(render_picker_html(manifest), encoding="utf-8")
    profile_metadata_path = Path(str(manifest["profile_metadata_template"]))
    profile_metadata_path.write_text(
        yaml.safe_dump(
            build_profile_metadata_template(clip_rows),
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    manual_picks_template_path = Path(str(manifest["manual_picks_template"]))
    manual_picks_template_path.write_text(
        json.dumps(
            build_manual_picks_template(clip_rows),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build keyframes, coordinate guides, QA, and sampling instructions.",
    )
    parser.add_argument("--input-dir", default="data/tests/real_video_clips")
    parser.add_argument("--output-dir", default="data/outputs/golden_calibration_packet")
    parser.add_argument("--clips", nargs="*", default=GOLDEN_CLIPS)
    parser.add_argument("--frame-index", type=int, default=1)
    parser.add_argument("--coordinate-step", type=int, default=160)
    parser.add_argument("--calibration-presets", default="data/tests/calibration_presets.yaml")
    parser.add_argument("--camera-profiles", default="data/tests/camera_profiles.yaml")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = build_packet(
        input_dir=Path(args.input_dir),
        output_dir=Path(args.output_dir),
        clips=args.clips,
        frame_index=args.frame_index,
        calibration_presets=Path(args.calibration_presets),
        camera_profiles=Path(args.camera_profiles),
        coordinate_step=args.coordinate_step,
    )
    print(
        json.dumps(
            {
                "clip_count": len(manifest["clips"]),
                "trusted_count": manifest["qa_summary"]["trusted_count"],
                "output_dir": manifest["output_dir"],
            },
            ensure_ascii=False,
            indent=2,
        ),
    )


if __name__ == "__main__":
    main()
