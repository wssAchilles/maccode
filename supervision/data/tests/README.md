# Test Video Dataset Notes

This folder contains local video samples for testing the supervision-based multi-object detection and tracking agent.

Last checked: 2026-05-28.

## Current Layout

```text
data/tests/
├── README.md
├── real_video_clips/
│   ├── 29 curated MP4 clips
│   └── manifest.csv
└── zenodo_traffic/
    └── 3 raw/source MP4 videos
```

Total videos currently present: 32.

Total folder size: about 716 MB.

## Main Test Clips

Path:

```text
/Users/achilles/Documents/code/supervision/data/tests/real_video_clips
```

This directory contains 29 curated MP4 clips. Most clips are 30 seconds long and are intended as the primary test inputs for the agent.

### 1. Wide Signalized Intersection Clips

Files:

```text
023_complex_signal_day_wide_0010s_30s.mp4
024_complex_signal_day_wide_0045s_30s.mp4
025_complex_signal_day_wide_0080s_30s.mp4
026_complex_signal_day_wide_0115s_30s.mp4
027_complex_signal_day_wide_0150s_30s.mp4
```

Type:

- Fixed elevated traffic-camera view.
- Wide intersection scene.
- Traffic signals are visible.
- Useful for vehicle detection, stop-line behavior, lane-level movement, and multi-vehicle tracking.

Resolution and frame rate:

- 1280x720
- 30 FPS
- 30 seconds each

### 2. Red-Light / Road-Camera Clips

Files:

```text
028_red_light_static_0008s_30s.mp4
029_red_light_static_0038s_30s.mp4
```

Type:

- Fixed road-camera view.
- Red-light / signalized-road scenarios.
- Useful for testing vehicle tracking near lights and intersection approaches.

Resolution and frame rate:

- 1280x720
- 30 FPS
- 30 seconds each

### 3. Pedestrian / Cyclist High-View Street Clips

Files:

```text
033_pedestrian_crowd_high_view_0000s_30s.mp4
034_pedestrian_crowd_high_view_0030s_30s.mp4
035_pedestrian_crowd_high_view_0060s_30s.mp4
036_pedestrian_crowd_high_view_0090s_30s.mp4
037_pedestrian_crowd_high_view_0120s_30s.mp4
038_pedestrian_crowd_high_view_0150s_30s.mp4
039_pedestrian_crowd_high_view_0180s_30s.mp4
040_pedestrian_crowd_high_view_0210s_30s.mp4
042_pedestrian_crowd_high_view_0270s_30s.mp4
```

Type:

- Fixed high CCTV-style street view.
- Dense pedestrians and some cyclists.
- Useful for person detection, crowd tracking, small-object tracking, and pedestrian flow analysis.

Resolution and frame rate:

- 1920x1080
- 25 FPS
- 30 seconds each

### 4. Dense Elevated 4K City Traffic Clips

Files:

```text
053_dense_city_traffic_4k_elevated_0000s_30s.mp4
054_dense_city_traffic_4k_elevated_0030s_30s.mp4
055_dense_city_traffic_4k_elevated_0060s_30s.mp4
056_dense_city_traffic_4k_elevated_0090s_30s.mp4
057_dense_city_traffic_4k_elevated_0120s_30s.mp4
058_dense_city_traffic_4k_elevated_0150s_30s.mp4
059_dense_city_traffic_4k_elevated_0180s_30s.mp4
060_dense_city_traffic_4k_elevated_0210s_30s.mp4
061_dense_city_traffic_4k_elevated_0240s_30s.mp4
062_dense_city_traffic_4k_elevated_0270s_30s.mp4
063_dense_city_traffic_4k_elevated_0300s_30s.mp4
064_dense_city_traffic_4k_elevated_0330s_30s.mp4
065_dense_city_traffic_4k_elevated_0360s_30s.mp4
```

Type:

- Fixed high/elevated camera view.
- Dense urban traffic with many cars and buses.
- Good stress-test material for multi-object vehicle detection and tracking.
- Best suited for evaluating performance on high-resolution, high-density traffic scenes.

Resolution and frame rate:

- 3840x2160
- 30 FPS
- 30 seconds each

## Raw Source Videos

Path:

```text
/Users/achilles/Documents/code/supervision/data/tests/zenodo_traffic
```

Files:

```text
teste2_6.mp4
video4.mp4
video6.mp4
```

Type:

- Raw Zenodo traffic source clips.
- These are not normalized into 30-second curated samples.
- They are useful for quick manual inspection or ad hoc tests, but they should not be treated as the primary benchmark set.

Current durations:

- `teste2_6.mp4`: about 95.6 seconds
- `video4.mp4`: about 17.9 seconds
- `video6.mp4`: about 8.9 seconds

Resolution and frame rate:

- 1280x720
- 30 FPS

## Metadata Notes

`real_video_clips/manifest.csv` exists, but it may include historical rows for files that were deleted manually. For automated evaluation, prefer scanning the files that actually exist in `real_video_clips/` instead of trusting the manifest blindly.

Recommended rule for the agent:

1. Use `real_video_clips/*.mp4` as the primary curated test set.
2. Use `zenodo_traffic/*.mp4` only as optional raw/source videos.
3. Ignore missing entries in `manifest.csv` if the referenced MP4 is not present on disk.

## Current Video Summary

By folder:

- `real_video_clips`: 29 videos
- `zenodo_traffic`: 3 videos

By resolution:

- 1280x720: 10 videos
- 1920x1080: 9 videos
- 3840x2160: 13 videos

By frame rate:

- 30 FPS: 23 videos
- 25 FPS: 9 videos

Use-case coverage:

- Signalized intersections
- Red-light / road-camera scenes
- Pedestrian and cyclist street scenes
- Dense elevated 4K city traffic
- Multi-object vehicle tracking
- Multi-person and small-object tracking
