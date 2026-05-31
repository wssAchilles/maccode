from __future__ import annotations

from scripts.build_golden_calibration_packet import (
    OPERATOR_CHECKLIST,
    WORLD_COORDINATE_PROTOCOL,
    build_manual_picks_template,
    build_profile_metadata_template,
    candidate_frame_indexes,
    render_markdown,
    render_picker_html,
)


def test_candidate_frame_indexes_include_requested_and_quartiles() -> None:
    metadata = {"frame_count": 901}

    assert candidate_frame_indexes(metadata, requested_frame=1) == [1, 225, 450, 675]


def test_packet_markdown_contains_sampling_protocol_and_acceptance_commands() -> None:
    manifest = {
        "output_dir": "data/outputs/golden_calibration_packet",
        "frame_index": 1,
        "picker_html": "data/outputs/golden_calibration_packet/golden_calibration_picker.html",
        "profile_metadata_template": "data/outputs/golden_calibration_packet/profile_metadata.yaml",
        "manual_picks_template": (
            "data/outputs/golden_calibration_packet/"
            "manual-golden-calibration-picks.template.json"
        ),
        "qa_summary": {
            "trusted_count": 0,
            "clip_count": 1,
            "clips": [
                {
                    "clip": "026_complex_signal_day_wide_0115s_30s.mp4",
                    "calibration_trusted": False,
                    "validation_max_error_px": 0.1,
                },
            ],
        },
        "clips": [
            {
                "clip": "026_complex_signal_day_wide_0115s_30s.mp4",
                "metadata": {"width": 1280, "height": 720},
                "keyframe": "keyframes/026.jpg",
                "coordinate_guide": "coordinate_guides/026.jpg",
                "line_candidate_guide": "line_guides/026.jpg",
                "candidate_frames": [
                    "candidate_frames/026_frame_1.jpg",
                    "candidate_frames/026_frame_225.jpg",
                ],
                "qa_image": "qa/026.jpg",
                "sampling_guide": ["Pick true ground-plane landmarks."],
            },
        ],
    }

    markdown = render_markdown(manifest)

    assert "Candidate frames" in markdown
    assert "Candidate ground-line guide" in markdown
    assert "profile_metadata.yaml" in markdown
    assert "manual-golden-calibration-picks.template.json" in markdown
    assert "suppressed" in markdown
    assert OPERATOR_CHECKLIST[0] in markdown
    assert WORLD_COORDINATE_PROTOCOL[0] in markdown
    assert "calibration_trusted: false" in markdown
    assert "road_plane_polygon_pixel" in markdown
    assert "--trusted` refuses incomplete evidence" in markdown
    assert "preflight_golden_calibration_picks.py" in markdown
    assert "merge_golden_calibration_picks.py" in markdown
    assert "run_golden_calibration_acceptance.py --run-analysis --strict" in markdown


def test_picker_html_contains_click_modes_and_yaml_export() -> None:
    manifest = {
        "output_dir": "data/outputs/golden_calibration_packet",
        "operator_checklist": OPERATOR_CHECKLIST,
        "world_coordinate_protocol": WORLD_COORDINATE_PROTOCOL,
        "clips": [
            {
                "clip": "026_complex_signal_day_wide_0115s_30s.mp4",
                "metadata": {"width": 1280, "height": 720},
                "coordinate_guide": "data/outputs/golden_calibration_packet/guide.jpg",
                "candidate_frames": [
                    "data/outputs/golden_calibration_packet/candidate_frames/026.jpg",
                ],
            },
        ],
    }

    html = render_picker_html(manifest)

    assert "control point" in html
    assert "validation segment" in html
    assert "road polygon pixel" in html
    assert "__profile_metadata__" in html
    assert "manual_ground_control_point_picker" in html
    assert "Evidence sources" in html
    assert "control_points" in html
    assert "validation_segments" in html
    assert "Scale prior description" in html
    assert "road_plane_polygon_pixel" in html
    assert "Copy YAML" in html


def test_profile_metadata_template_requires_replacement_text() -> None:
    metadata = build_profile_metadata_template(
        [{"clip": "026_complex_signal_day_wide_0115s_30s.mp4"}],
    )

    assert metadata["026_complex_signal_day_wide_0115s_30s.mp4"][
        "scale_prior_description"
    ].startswith("REPLACE")
    assert (
        metadata["026_complex_signal_day_wide_0115s_30s.mp4"]["annotation_method"]
        == "manual_ground_control_point_picker"
    )
    assert "manual_pixel_clicks_on_exported_keyframe" in metadata[
        "026_complex_signal_day_wide_0115s_30s.mp4"
    ]["evidence_sources"]


def test_manual_picks_template_uses_explicit_manual_fields() -> None:
    template = build_manual_picks_template(
        [{"clip": "026_complex_signal_day_wide_0115s_30s.mp4"}],
    )

    clip_template = template["026_complex_signal_day_wide_0115s_30s.mp4"]
    assert clip_template["annotation_method"] == "manual_ground_control_point_picker"
    assert clip_template["control_points"] == []
    assert clip_template["validation_segments"] == []
    assert clip_template["road_plane_polygon_pixel"] == []
    assert "manual_pixel_clicks_on_exported_keyframe" in clip_template[
        "evidence_sources"
    ]
