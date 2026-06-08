from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from domain.speed.geometry_diagnostics import (
    TrackGeometryDiagnosticBuilder,
    reports_from_analysis_payload,
)
from shared.configs.settings import Settings

from scripts.analyze_real_videos import (
    CalibrationPresetCatalog,
    analyze_clip,
    load_calibration_presets,
    load_camera_profiles,
    resolve_device,
    select_clips,
    summarize,
)
from scripts.audit_golden_calibration import audit_acceptance_table
from scripts.audit_golden_calibration import render_markdown as render_audit_markdown
from scripts.build_calibration_qa import GOLDEN_CLIPS, build_qa_summary
from scripts.build_calibration_readiness_report import build_readiness_report
from scripts.build_golden_acceptance_table import build_acceptance_table
from scripts.build_math_model_card import build_model_card
from scripts.build_math_model_card import render_markdown as render_model_card_markdown


def write_audit_outputs(payload: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "golden_calibration_audit.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "golden_calibration_audit.md").write_text(
        render_audit_markdown(payload),
        encoding="utf-8",
    )


def write_math_model_cards(
    *,
    analysis_output_dir: Path,
    readiness_json: Path | None,
    clips: list[str],
) -> None:
    cards_root = analysis_output_dir / "math_model_cards"
    for clip in clips:
        analysis_path = analysis_output_dir / f"{Path(clip).stem}.json"
        if not analysis_path.exists():
            continue
        card = build_model_card(analysis_path, readiness_json)
        output_dir = cards_root / Path(clip).stem
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "math_model_card.json").write_text(
            json.dumps(card, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (output_dir / "math_model_card.md").write_text(
            render_model_card_markdown(card),
            encoding="utf-8",
        )


def run_real_analysis(
    *,
    input_dir: Path,
    output_dir: Path,
    calibration_presets: Path,
    camera_profiles: Path,
    clips: list[str],
    max_frames: int | None,
    frame_stride: int,
    confidence: float,
    model_path: str | None,
    device: str,
) -> Path:
    settings = Settings()
    resolved_model_path = model_path or settings.cv.yolo_model
    resolved_device = resolve_device(device)
    presets = load_calibration_presets(calibration_presets)
    presets = CalibrationPresetCatalog(
        scene_profiles=presets.scene_profiles,
        video_calibrations=presets.video_calibrations,
        camera_profiles=load_camera_profiles(camera_profiles),
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    selected_clips = select_clips(
        input_dir,
        limit=len(clips),
        sample_per_profile=0,
        presets=presets,
        clip_names=clips,
    )
    results: list[dict[str, Any]] = []
    for path in selected_clips:
        try:
            result = analyze_clip(
                path=path,
                model_path=resolved_model_path,
                device=resolved_device,
                confidence=confidence,
                frame_stride=frame_stride,
                max_frames=max_frames,
                presets=presets,
                processed_output_dir=output_dir / "processed_videos",
            )
            result["status"] = "ok"
        except Exception as exc:  # noqa: BLE001
            result = {"clip": path.name, "status": "failed", "error": str(exc)}
        results.append(result)
        (output_dir / f"{path.stem}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    summary_payload = {"summary": summarize(results), "results": results}
    summary_path = output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary_path


def run_pipeline(
    *,
    input_dir: Path,
    calibration_presets: Path,
    camera_profiles: Path,
    analysis_summary: Path,
    analysis_output_dir: Path,
    qa_output_dir: Path,
    acceptance_output_dir: Path,
    readiness_output_dir: Path,
    audit_output_dir: Path,
    clips: list[str],
    frame_index: int,
    project_root: Path,
    run_analysis: bool = False,
    max_frames: int | None = 45,
    frame_stride: int = 15,
    confidence: float = 0.35,
    model_path: str | None = None,
    device: str = "auto",
    tracker_id: int | None = None,
    strict_track_geometry: bool = False,
) -> dict[str, Any]:
    if run_analysis:
        analysis_summary = run_real_analysis(
            input_dir=input_dir,
            output_dir=analysis_output_dir,
            calibration_presets=calibration_presets,
            camera_profiles=camera_profiles,
            clips=clips,
            max_frames=max_frames,
            frame_stride=frame_stride,
            confidence=confidence,
            model_path=model_path,
            device=device,
        )
    qa_summary = build_qa_summary(
        input_dir=input_dir,
        output_dir=qa_output_dir,
        calibration_presets=calibration_presets,
        camera_profiles=camera_profiles,
        clips=clips,
        frame_index=frame_index,
    )
    acceptance = build_acceptance_table(
        qa_summary_path=qa_output_dir / "calibration_qa_summary.json",
        analysis_summary_path=analysis_summary,
        output_dir=acceptance_output_dir,
    )
    readiness = build_readiness_report(
        acceptance_path=acceptance_output_dir / "golden_acceptance_table.json",
        output_dir=readiness_output_dir,
    )
    if run_analysis:
        write_math_model_cards(
            analysis_output_dir=analysis_summary.parent,
            readiness_json=readiness_output_dir / "calibration_readiness_report.json",
            clips=clips,
        )
    audit = audit_acceptance_table(acceptance, project_root=project_root)
    write_audit_outputs(audit, audit_output_dir)
    track_geometry = _track_geometry_acceptance(
        analysis_output_dir=analysis_summary.parent,
        clips=clips,
        tracker_id=tracker_id,
    )
    if strict_track_geometry and track_geometry and not all(
        item["passed"] for item in track_geometry
    ):
        raise SystemExit(1)
    return {
        "qa": {
            "clip_count": qa_summary["clip_count"],
            "trusted_count": qa_summary["trusted_count"],
            "output_dir": str(qa_output_dir),
        },
        "acceptance": {
            "clip_count": acceptance["clip_count"],
            "trusted_count": acceptance["trusted_count"],
            "output_dir": str(acceptance_output_dir),
        },
        "readiness": {
            "clip_count": readiness["clip_count"],
            "trusted_count": readiness["trusted_count"],
            "ready_for_defense_count": readiness["ready_for_defense_count"],
            "output_dir": str(readiness_output_dir),
        },
        "audit": {
            "defense_ready_count": audit["defense_ready_count"],
            "required_clip_count": audit["required_clip_count"],
            "all_defense_ready": audit["all_defense_ready"],
            "output_dir": str(audit_output_dir),
        },
        "track_geometry": track_geometry,
    }


def _track_geometry_acceptance(
    *,
    analysis_output_dir: Path,
    clips: list[str],
    tracker_id: int | None,
) -> list[dict[str, Any]]:
    if tracker_id is None:
        return []
    rows: list[dict[str, Any]] = []
    for clip in clips:
        analysis_path = analysis_output_dir / f"{Path(clip).stem}.json"
        if not analysis_path.exists():
            rows.append({"clip": clip, "passed": False, "reason": "analysis_json_missing"})
            continue
        payload = json.loads(analysis_path.read_text(encoding="utf-8"))
        diagnostic = TrackGeometryDiagnosticBuilder().build(
            reports_from_analysis_payload(payload),
            tracker_id=tracker_id,
        )
        golden = diagnostic.metrics.get("golden_acceptance")
        passed = bool(golden.get("passed")) if isinstance(golden, dict) else False
        rows.append(
            {
                "clip": clip,
                "tracker_id": tracker_id,
                "passed": passed,
                "root_cause_verdicts": diagnostic.metrics.get("root_cause_verdicts", []),
                "golden_acceptance": golden,
            },
        )
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the four-clip golden calibration acceptance chain: "
            "QA images -> acceptance table -> readiness report -> final audit."
        ),
    )
    parser.add_argument("--input-dir", default="data/tests/real_video_clips")
    parser.add_argument("--calibration-presets", default="data/tests/calibration_presets.yaml")
    parser.add_argument("--camera-profiles", default="data/tests/camera_profiles.yaml")
    parser.add_argument(
        "--analysis-summary",
        default="data/outputs/golden_acceptance_smoke/summary.json",
    )
    parser.add_argument(
        "--analysis-output-dir",
        default="data/outputs/golden_acceptance_smoke",
    )
    parser.add_argument("--qa-output-dir", default="data/outputs/calibration_qa")
    parser.add_argument(
        "--acceptance-output-dir",
        default="data/outputs/golden_acceptance_table",
    )
    parser.add_argument(
        "--readiness-output-dir",
        default="data/outputs/calibration_readiness",
    )
    parser.add_argument(
        "--audit-output-dir",
        default="data/outputs/golden_calibration_audit",
    )
    parser.add_argument("--clips", nargs="*", default=GOLDEN_CLIPS)
    parser.add_argument("--frame-index", type=int, default=1)
    parser.add_argument(
        "--run-analysis",
        action="store_true",
        help="Rerun YOLO/supervision processing before building acceptance outputs.",
    )
    parser.add_argument("--max-frames", type=int, default=45)
    parser.add_argument("--frame-stride", type=int, default=15)
    parser.add_argument("--confidence", type=float, default=0.35)
    parser.add_argument("--model", default=None)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--tracker-id", type=int, default=None)
    parser.add_argument(
        "--strict-track-geometry",
        action="store_true",
        help="Exit 1 unless the selected tracker passes golden track geometry gates.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with status 1 unless all four golden clips pass final audit.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_pipeline(
        input_dir=Path(args.input_dir),
        calibration_presets=Path(args.calibration_presets),
        camera_profiles=Path(args.camera_profiles),
        analysis_summary=Path(args.analysis_summary),
        analysis_output_dir=Path(args.analysis_output_dir),
        qa_output_dir=Path(args.qa_output_dir),
        acceptance_output_dir=Path(args.acceptance_output_dir),
        readiness_output_dir=Path(args.readiness_output_dir),
        audit_output_dir=Path(args.audit_output_dir),
        clips=list(args.clips),
        frame_index=args.frame_index,
        project_root=Path.cwd(),
        run_analysis=args.run_analysis,
        max_frames=args.max_frames if args.max_frames > 0 else None,
        frame_stride=args.frame_stride,
        confidence=args.confidence,
        model_path=args.model,
        device=args.device,
        tracker_id=args.tracker_id,
        strict_track_geometry=args.strict_track_geometry,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.strict and not result["audit"]["all_defense_ready"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
