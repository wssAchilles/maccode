import { type MouseEvent, useEffect, useMemo, useRef, useState } from "react";

import { getCalibrationPreset, saveCalibrationPreset } from "../api/calibration";
import { listVideoSamples, sampleVideoUrl } from "../api/video";
import type {
  CalibrationEntry,
  CalibrationPoint,
  CalibrationSaveResult,
  ValidationSegment
} from "../types/calibration";
import type { VideoSample } from "../types/videoTask";

const defaultWorldPoints = [
  { world_x: 0, world_y: 0 },
  { world_x: 24, world_y: 0 },
  { world_x: 24, world_y: 65 },
  { world_x: 0, world_y: 65 }
];
const minTrustedControlPoints = 8;
const minTrustedValidationSegments = 2;
const usableValidationGatePx = 15;

type PickTarget =
  | "control_point"
  | "segment_pixel_start"
  | "segment_pixel_end"
  | "road_polygon_pixel";

function pairMatchesControlPoint(
  point: CalibrationPoint,
  pixel: [number, number],
  world: [number, number],
  tolerance = 1e-6
) {
  return (
    Math.abs(point.pixel_x - pixel[0]) <= tolerance &&
    Math.abs(point.pixel_y - pixel[1]) <= tolerance &&
    Math.abs(point.world_x - world[0]) <= tolerance &&
    Math.abs(point.world_y - world[1]) <= tolerance
  );
}

function isIndependentValidationSegment(
  points: CalibrationPoint[],
  segment: ValidationSegment
) {
  const startReusesControlPoint = points.some((point) =>
    pairMatchesControlPoint(point, segment.pixel_start, segment.world_start)
  );
  const endReusesControlPoint = points.some((point) =>
    pairMatchesControlPoint(point, segment.pixel_end, segment.world_end)
  );
  return !(startReusesControlPoint && endReusesControlPoint);
}

function worldExtent(
  roadWorldPolygon: Array<[number, number]>,
  points: CalibrationPoint[]
) {
  const worldPairs =
    roadWorldPolygon.length >= 3
      ? roadWorldPolygon
      : points.map((point) => [point.world_x, point.world_y] as [number, number]);
  if (worldPairs.length === 0) {
    return { width: 0, length: 0 };
  }
  const xs = worldPairs.map((pair) => pair[0]);
  const ys = worldPairs.map((pair) => pair[1]);
  return {
    width: Math.max(...xs) - Math.min(...xs),
    length: Math.max(...ys) - Math.min(...ys)
  };
}

export function CalibrationWorkbench() {
  const [imageUrl, setImageUrl] = useState("");
  const [imageObjectUrl, setImageObjectUrl] = useState<string | null>(null);
  const [videoObjectUrl, setVideoObjectUrl] = useState<string | null>(null);
  const [imageLoadFailed, setImageLoadFailed] = useState(false);
  const [imageSize, setImageSize] = useState({ width: 1280, height: 720 });
  const [clipName, setClipName] = useState("028_red_light_static_0008s_30s.mp4");
  const [samples, setSamples] = useState<VideoSample[]>([]);
  const [positionRmseFloorM, setPositionRmseFloorM] = useState(0.75);
  const [scaleUncertaintyPct, setScaleUncertaintyPct] = useState(4);
  const [declaredTrusted, setDeclaredTrusted] = useState(false);
  const [scalePriorKind, setScalePriorKind] = useState("traffic_standard_or_survey");
  const [scalePriorDescription, setScalePriorDescription] = useState("");
  const [profileNotes, setProfileNotes] = useState("");
  const [roadPixelPolygonText, setRoadPixelPolygonText] = useState("[]");
  const [roadPolygonText, setRoadPolygonText] = useState(
    "[[0,0],[24,0],[24,65],[0,65]]"
  );
  const [validationSegmentsText, setValidationSegmentsText] = useState("[]");
  const [segmentName, setSegmentName] = useState("validation_segment");
  const [segmentPixelStart, setSegmentPixelStart] = useState<[number, number]>([0, 0]);
  const [segmentPixelEnd, setSegmentPixelEnd] = useState<[number, number]>([0, 0]);
  const [segmentWorldStart, setSegmentWorldStart] = useState<[number, number]>([0, 0]);
  const [segmentWorldEnd, setSegmentWorldEnd] = useState<[number, number]>([0, 0]);
  const [pickTarget, setPickTarget] = useState<PickTarget>("control_point");
  const [activeIndex, setActiveIndex] = useState(0);
  const [saveResult, setSaveResult] = useState<CalibrationSaveResult | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [points, setPoints] = useState<CalibrationPoint[]>(
    defaultWorldPoints.map((point) => ({
      pixel_x: 0,
      pixel_y: 0,
      ...point
    }))
  );
  const videoRef = useRef<HTMLVideoElement | null>(null);

  function selectSample(sampleName: string) {
    if (videoObjectUrl?.startsWith("blob:")) {
      URL.revokeObjectURL(videoObjectUrl);
    }
    setClipName(sampleName);
    setVideoObjectUrl(sampleVideoUrl(sampleName));
    setImageObjectUrl(null);
    setImageUrl("");
    setImageLoadFailed(false);
    setSaveResult(null);
    setSaveError(null);
  }

  useEffect(
    () => () => {
      if (imageObjectUrl) {
        URL.revokeObjectURL(imageObjectUrl);
      }
      if (videoObjectUrl?.startsWith("blob:")) {
        URL.revokeObjectURL(videoObjectUrl);
      }
    },
    [imageObjectUrl, videoObjectUrl]
  );

  useEffect(() => {
    let isMounted = true;
    listVideoSamples()
      .then((nextSamples) => {
        if (!isMounted) {
          return;
        }
        setSamples(nextSamples);
        if (nextSamples.length > 0) {
          setClipName(nextSamples[0].name);
        }
      })
      .catch(() => {
        if (isMounted) {
          setSamples([]);
        }
      });
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    let isMounted = true;
    if (!clipName) {
      return undefined;
    }
    getCalibrationPreset(clipName)
      .then((entry) => {
        if (!isMounted || !entry) {
          return;
        }
        setPositionRmseFloorM(entry.position_rmse_floor_m);
        setScaleUncertaintyPct(entry.calibration_scale_uncertainty_pct);
        setDeclaredTrusted(Boolean(entry.calibration_trusted));
        setScalePriorKind(String(entry.scale_prior?.kind ?? "traffic_standard_or_survey"));
        setScalePriorDescription(String(entry.scale_prior?.description ?? ""));
        setProfileNotes(entry.profile_notes ?? "");
        setRoadPixelPolygonText(JSON.stringify(entry.road_plane_polygon_pixel ?? []));
        setRoadPolygonText(JSON.stringify(entry.road_plane_polygon_world ?? []));
        setValidationSegmentsText(JSON.stringify(entry.validation_segments ?? [], null, 2));
        setPoints(entry.points);
      })
      .catch(() => undefined);
    return () => {
      isMounted = false;
    };
  }, [clipName]);

  const calibrationEntry: CalibrationEntry = useMemo(
    () => ({
      notes: "Manual calibration from frontend workbench.",
      position_rmse_floor_m: positionRmseFloorM,
      calibration_scale_uncertainty_pct: scaleUncertaintyPct,
      calibration_trusted: declaredTrusted,
      scale_prior: {
        kind: scalePriorKind.trim(),
        description: scalePriorDescription.trim()
      },
      profile_notes: profileNotes.trim(),
      road_plane_polygon_pixel: parseJsonField<Array<[number, number]>>(
        roadPixelPolygonText,
        []
      ),
      road_plane_polygon_world: parseJsonField<Array<[number, number]>>(roadPolygonText, []),
      validation_segments: parseJsonField<ValidationSegment[]>(validationSegmentsText, []),
      points
    }),
    [
      declaredTrusted,
      points,
      profileNotes,
      positionRmseFloorM,
      roadPixelPolygonText,
      roadPolygonText,
      scalePriorDescription,
      scalePriorKind,
      scaleUncertaintyPct,
      validationSegmentsText
    ]
  );

  const exportPayload = useMemo(
    () => ({
      [clipName]: calibrationEntry
    }),
    [calibrationEntry, clipName]
  );

  const fullPresetPayload = useMemo(
    () => ({
      schema_version: 1,
      notes: "Generated by TrafficPerceptionEngine calibration workbench.",
      video_calibrations: exportPayload
    }),
    [exportPayload]
  );
  const activeImageSrc = imageObjectUrl ?? imageUrl.trim();
  const validationSegments = useMemo(
    () => parseJsonField<ValidationSegment[]>(validationSegmentsText, []),
    [validationSegmentsText]
  );
  const independentValidationSegmentCount = useMemo(
    () =>
      validationSegments.filter((segment) =>
        isIndependentValidationSegment(points, segment)
      ).length,
    [points, validationSegments]
  );
  const roadPixelPolygon = useMemo(
    () => parseJsonField<Array<[number, number]>>(roadPixelPolygonText, []),
    [roadPixelPolygonText]
  );
  const roadWorldPolygon = useMemo(
    () => parseJsonField<Array<[number, number]>>(roadPolygonText, []),
    [roadPolygonText]
  );
  const goldenPickerPayload = useMemo(() => {
    const extent = worldExtent(roadWorldPolygon, points);
    return {
      [clipName]: {
        points: points.map((point) => ({
          pixel: [point.pixel_x, point.pixel_y],
          world: [point.world_x, point.world_y]
        })),
        segments: validationSegments,
        polygon: roadPixelPolygon
      },
      __profile_metadata__: {
        [clipName]: {
          world_width_m: extent.width,
          world_length_m: extent.length,
          position_rmse_floor_m: positionRmseFloorM,
          calibration_scale_uncertainty_pct: scaleUncertaintyPct,
          scale_prior_kind: scalePriorKind.trim(),
          scale_prior_description: scalePriorDescription.trim(),
          profile_notes: profileNotes.trim(),
          road_plane_polygon_world: roadWorldPolygon
        }
      }
    };
  }, [
    clipName,
    points,
    positionRmseFloorM,
    profileNotes,
    roadPixelPolygon,
    roadWorldPolygon,
    scalePriorDescription,
    scalePriorKind,
    scaleUncertaintyPct,
    validationSegments
  ]);
  const localGateChecks = useMemo(
    () => [
      {
        label: "同一地面控制点",
        passed: points.length >= minTrustedControlPoints,
        value: `${points.length}/${minTrustedControlPoints}`
      },
      {
        label: "验证线段总数",
        passed: validationSegments.length >= minTrustedValidationSegments,
        value: `${validationSegments.length}/${minTrustedValidationSegments}`
      },
      {
        label: "本地独立验证线",
        passed: independentValidationSegmentCount >= minTrustedValidationSegments,
        value: `${independentValidationSegmentCount}/${minTrustedValidationSegments}`
      },
      {
        label: "尺度先验证据",
        passed: scalePriorDescription.trim().length > 0,
        value: scalePriorDescription.trim() ? "已填写" : "缺失"
      },
      {
        label: "Profile 说明",
        passed: profileNotes.trim().length > 0,
        value: profileNotes.trim() ? "已填写" : "缺失"
      },
      {
        label: "像素地面区域",
        passed: roadPixelPolygon.length >= 3,
        value: `${roadPixelPolygon.length}/3`
      },
      {
        label: "米制地面区域",
        passed: roadWorldPolygon.length >= 3,
        value: `${roadWorldPolygon.length}/3`
      },
      {
        label: "声明可信",
        passed: declaredTrusted,
        value: declaredTrusted ? "true" : "false"
      }
    ],
    [
      declaredTrusted,
      independentValidationSegmentCount,
      profileNotes,
      points.length,
      roadPixelPolygon.length,
      roadWorldPolygon.length,
      scalePriorDescription,
      validationSegments.length
    ]
  );
  const savedGateChecks = useMemo(() => {
    if (!saveResult) {
      return [];
    }
    const validation = saveResult.diagnostics.validation_max_error_px;
    return [
      {
        label: "独立验证线通过",
        passed: Boolean(saveResult.diagnostics.validation_segments_independent),
        value: String(saveResult.diagnostics.independent_validation_segment_count ?? 0)
      },
      {
        label: "验证误差",
        passed: validation != null && validation <= usableValidationGatePx,
        value: validation == null ? "N/A" : `${validation.toFixed(3)} px`
      },
      {
        label: "最终可信",
        passed: Boolean(saveResult.diagnostics.calibration_trusted),
        value: String(saveResult.diagnostics.calibration_trusted ?? false)
      }
    ];
  }, [saveResult]);

  function handleImageClick(event: MouseEvent<HTMLImageElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    const scaleX = event.currentTarget.naturalWidth / rect.width;
    const scaleY = event.currentTarget.naturalHeight / rect.height;
    setImageSize({
      width: event.currentTarget.naturalWidth,
      height: event.currentTarget.naturalHeight
    });
    const pixelX = (event.clientX - rect.left) * scaleX;
    const pixelY = (event.clientY - rect.top) * scaleY;
    const nextPixel: [number, number] = [
      Number(pixelX.toFixed(2)),
      Number(pixelY.toFixed(2))
    ];
    if (pickTarget === "segment_pixel_start") {
      setSegmentPixelStart(nextPixel);
      setPickTarget("segment_pixel_end");
      return;
    }
    if (pickTarget === "segment_pixel_end") {
      setSegmentPixelEnd(nextPixel);
      setPickTarget("control_point");
      return;
    }
    if (pickTarget === "road_polygon_pixel") {
      setRoadPixelPolygonText(JSON.stringify([...roadPixelPolygon, nextPixel]));
      return;
    }
    setPoints((current) =>
      current.map((point, index) =>
        index === activeIndex
          ? { ...point, pixel_x: nextPixel[0], pixel_y: nextPixel[1] }
          : point
      )
    );
    setActiveIndex((activeIndex + 1) % points.length);
  }

  function updateWorldPoint(index: number, key: "world_x" | "world_y", value: string) {
    const numeric = Number(value);
    setPoints((current) =>
      current.map((point, pointIndex) =>
        pointIndex === index && Number.isFinite(numeric) ? { ...point, [key]: numeric } : point
      )
    );
  }

  function parseJsonField<T>(value: string, fallback: T): T {
    try {
      return JSON.parse(value) as T;
    } catch {
      return fallback;
    }
  }

  function handleImageFile(file: File | undefined) {
    if (!file) {
      return;
    }
    setImageLoadFailed(false);
    setImageObjectUrl(URL.createObjectURL(file));
    setImageUrl(file.name);
  }

  function handleVideoFile(file: File | undefined) {
    if (!file) {
      return;
    }
    if (videoObjectUrl?.startsWith("blob:")) {
      URL.revokeObjectURL(videoObjectUrl);
    }
    setClipName(file.name);
    setVideoObjectUrl(URL.createObjectURL(file));
    setSaveResult(null);
    setSaveError(null);
  }

  function captureVideoFrame() {
    const video = videoRef.current;
    if (!video || video.videoWidth <= 0 || video.videoHeight <= 0) {
      return;
    }
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    if (imageObjectUrl) {
      URL.revokeObjectURL(imageObjectUrl);
    }
    setImageObjectUrl(null);
    setImageLoadFailed(false);
    setImageSize({ width: canvas.width, height: canvas.height });
    setImageUrl(canvas.toDataURL("image/jpeg", 0.92));
  }

  function addControlPoint() {
    setPoints((current) => {
      if (current.length >= 10) {
        return current;
      }
      const last = current[current.length - 1] ?? {
        pixel_x: 0,
        pixel_y: 0,
        world_x: 0,
        world_y: 0
      };
      return [
        ...current,
        {
          pixel_x: 0,
          pixel_y: 0,
          world_x: last.world_x,
          world_y: last.world_y + 5
        }
      ];
    });
    setActiveIndex(points.length);
  }

  function removeLastControlPoint() {
    setPoints((current) => (current.length > 4 ? current.slice(0, -1) : current));
    setActiveIndex((current) => Math.min(current, Math.max(0, points.length - 2)));
  }

  function updateRoadPolygonFromFirstFourPoints() {
    const polygon = points.slice(0, 4).map((point) => [point.world_x, point.world_y]);
    const pixelPolygon = points.slice(0, 4).map((point) => [point.pixel_x, point.pixel_y]);
    setRoadPixelPolygonText(JSON.stringify(pixelPolygon));
    setRoadPolygonText(JSON.stringify(polygon));
  }

  function clearRoadPixelPolygon() {
    setRoadPixelPolygonText("[]");
    setPickTarget("road_polygon_pixel");
  }

  function updateSegmentTuple(
    setter: (value: [number, number]) => void,
    tuple: [number, number],
    tupleIndex: 0 | 1,
    value: string
  ) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
      return;
    }
    const next: [number, number] = [...tuple];
    next[tupleIndex] = numeric;
    setter(next);
  }

  function addIndependentValidationSegment() {
    const nextSegment: ValidationSegment = {
      name: segmentName.trim() || `validation_${validationSegments.length + 1}`,
      pixel_start: segmentPixelStart,
      pixel_end: segmentPixelEnd,
      world_start: segmentWorldStart,
      world_end: segmentWorldEnd
    };
    setValidationSegmentsText(JSON.stringify([...validationSegments, nextSegment], null, 2));
    setSegmentName(`validation_${validationSegments.length + 2}`);
    setPickTarget("segment_pixel_start");
  }

  function removeValidationSegment(indexToRemove: number) {
    setValidationSegmentsText(
      JSON.stringify(
        validationSegments.filter((_, index) => index !== indexToRemove),
        null,
        2
      )
    );
  }

  async function saveToYaml() {
    setIsSaving(true);
    setSaveError(null);
    setSaveResult(null);
    try {
      const result = await saveCalibrationPreset({
        clip_name: clipName,
        ...calibrationEntry,
        frame_width: imageSize.width,
        frame_height: imageSize.height,
        grid_spacing_m: 5.0
      });
      setSaveResult(result);
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "保存标定失败");
    } finally {
      setIsSaving(false);
    }
  }

  function downloadJson(filename: string, payload: object) {
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json"
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="calibration-workbench">
      <section className="panel wide">
        <div className="panel-heading">
          <h2>人工标定工作台</h2>
        </div>
        <div className="calibration-controls">
          <label>
            <span>真实样片</span>
            <select
              disabled={samples.length === 0}
              onChange={(event) => selectSample(event.target.value)}
              value={clipName}
            >
              {samples.map((sample) => (
                <option key={sample.name} value={sample.name}>
                  {sample.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>视频文件名</span>
            <input onChange={(event) => setClipName(event.target.value)} value={clipName} />
          </label>
          <label>
            <span>标定帧路径</span>
            <input
              onChange={(event) => {
                setImageObjectUrl(null);
                setImageLoadFailed(false);
                setImageUrl(event.target.value);
              }}
              placeholder="选择本地标定图，或粘贴可访问 URL"
              value={imageUrl}
            />
          </label>
          <label>
            <span>本地 MP4</span>
            <input
              accept="video/mp4"
              onChange={(event) => handleVideoFile(event.target.files?.[0])}
              type="file"
            />
          </label>
          <label>
            <span>选择标定图</span>
            <input
              accept="image/jpeg,image/png"
              onChange={(event) => handleImageFile(event.target.files?.[0])}
              type="file"
            />
          </label>
          <label>
            <span>位置 RMSE floor/m</span>
            <input
              onChange={(event) => setPositionRmseFloorM(Number(event.target.value))}
              step="0.05"
              type="number"
              value={positionRmseFloorM}
            />
          </label>
          <label>
            <span>尺度不确定性/%</span>
            <input
              onChange={(event) => setScaleUncertaintyPct(Number(event.target.value))}
              step="0.5"
              type="number"
              value={scaleUncertaintyPct}
            />
          </label>
          <label>
            <span>尺度先验类型</span>
            <input
              onChange={(event) => setScalePriorKind(event.target.value)}
              value={scalePriorKind}
            />
          </label>
          <label>
            <span>尺度先验证据</span>
            <input
              onChange={(event) => setScalePriorDescription(event.target.value)}
              placeholder="例如：车道宽约 3.5m，来自道路规范/现场测量"
              value={scalePriorDescription}
            />
          </label>
          <label className="wide-field">
            <span>Profile 说明</span>
            <input
              onChange={(event) => setProfileNotes(event.target.value)}
              placeholder="说明固定机位、地面平面、尺度来源和适用范围"
              value={profileNotes}
            />
          </label>
          <label>
            <span>声明 trusted</span>
            <select
              onChange={(event) => setDeclaredTrusted(event.target.value === "true")}
              value={String(declaredTrusted)}
            >
              <option value="false">false - 等待验证</option>
              <option value="true">true - 需验证段通过</option>
            </select>
          </label>
        </div>
      </section>

      <section className="panel calibration-image-panel">
        <div className="panel-heading">
          <h2>
            {pickTarget === "control_point"
              ? `点击 P${activeIndex + 1}`
              : pickTarget === "segment_pixel_start"
                ? "点击验证段像素起点"
                : pickTarget === "segment_pixel_end"
                  ? "点击验证段像素终点"
                  : "点击地面区域边界点"}
          </h2>
          <div className="button-row">
            <button
              className="secondary-button"
              disabled={!videoObjectUrl}
              onClick={captureVideoFrame}
              type="button"
            >
              捕获视频帧
            </button>
            <button
              className={pickTarget === "control_point" ? "primary-button" : "secondary-button"}
              onClick={() => setPickTarget("control_point")}
              type="button"
            >
              控制点模式
            </button>
            <button
              className={
                pickTarget !== "control_point" ? "primary-button" : "secondary-button"
              }
              onClick={() => setPickTarget("segment_pixel_start")}
              type="button"
            >
              验证线模式
            </button>
            <button
              className={
                pickTarget === "road_polygon_pixel" ? "primary-button" : "secondary-button"
              }
              onClick={() => setPickTarget("road_polygon_pixel")}
              type="button"
            >
              地面区域模式
            </button>
          </div>
        </div>
        {videoObjectUrl && (
          <video
            className="calibration-video"
            controls
            muted
            playsInline
            ref={videoRef}
            src={videoObjectUrl}
          />
        )}
        <div className="calibration-image-wrap">
          {activeImageSrc && !imageLoadFailed ? (
            <img
              alt="calibration frame"
              onClick={handleImageClick}
              onError={() => setImageLoadFailed(true)}
              onLoad={(event) => {
                setImageLoadFailed(false);
                setImageSize({
                  width: event.currentTarget.naturalWidth,
                  height: event.currentTarget.naturalHeight
                });
              }}
              src={activeImageSrc}
            />
          ) : (
            <div className="calibration-empty-state">
              选择 MP4 后捕获当前帧，或选择一张标定帧后开始采集控制点
            </div>
          )}
          {activeImageSrc &&
            !imageLoadFailed &&
            (roadPixelPolygon.length > 0 ||
              validationSegments.length > 0 ||
              segmentPixelStart[0] > 0 ||
              segmentPixelStart[1] > 0 ||
              segmentPixelEnd[0] > 0 ||
              segmentPixelEnd[1] > 0) && (
            <svg
              aria-hidden="true"
              className="calibration-geometry-overlay"
              preserveAspectRatio="none"
              viewBox={`0 0 ${imageSize.width} ${imageSize.height}`}
            >
              {roadPixelPolygon.length > 0 && (
                <polygon
                  className="road-polygon-overlay"
                  points={roadPixelPolygon.map((point) => point.join(",")).join(" ")}
                />
              )}
              {validationSegments.map((segment, index) => (
                <g key={`${segment.name}-${index}`}>
                  <line
                    x1={segment.pixel_start[0]}
                    x2={segment.pixel_end[0]}
                    y1={segment.pixel_start[1]}
                    y2={segment.pixel_end[1]}
                  />
                  <text x={segment.pixel_start[0]} y={segment.pixel_start[1]}>
                    {segment.name}
                  </text>
                </g>
              ))}
              {(segmentPixelStart[0] > 0 || segmentPixelStart[1] > 0) &&
                (segmentPixelEnd[0] > 0 || segmentPixelEnd[1] > 0) && (
                  <line
                    className="draft-validation-line"
                    x1={segmentPixelStart[0]}
                    x2={segmentPixelEnd[0]}
                    y1={segmentPixelStart[1]}
                    y2={segmentPixelEnd[1]}
                  />
                )}
            </svg>
          )}
          {roadPixelPolygon.map((point, index) => (
            <span
              className="road-polygon-marker"
              key={`${point[0]}-${point[1]}-${index}`}
              style={{
                left: `${(point[0] / imageSize.width) * 100}%`,
                top: `${(point[1] / imageSize.height) * 100}%`
              }}
            >
              {`R${index + 1}`}
            </span>
          ))}
          {points.map((point, index) =>
            point.pixel_x > 0 || point.pixel_y > 0 ? (
              <span
                className={index === activeIndex ? "calibration-marker active" : "calibration-marker"}
                key={`${point.pixel_x}-${point.pixel_y}-${index}`}
                style={{
                  left: `${(point.pixel_x / imageSize.width) * 100}%`,
                  top: `${(point.pixel_y / imageSize.height) * 100}%`
                }}
              >
                {`P${index + 1}`}
              </span>
            ) : null
          )}
          {(segmentPixelStart[0] > 0 || segmentPixelStart[1] > 0) && (
            <span
              className="validation-endpoint-marker"
              style={{
                left: `${(segmentPixelStart[0] / imageSize.width) * 100}%`,
                top: `${(segmentPixelStart[1] / imageSize.height) * 100}%`
              }}
            >
              VS
            </span>
          )}
          {(segmentPixelEnd[0] > 0 || segmentPixelEnd[1] > 0) && (
            <span
              className="validation-endpoint-marker end"
              style={{
                left: `${(segmentPixelEnd[0] / imageSize.width) * 100}%`,
                top: `${(segmentPixelEnd[1] / imageSize.height) * 100}%`
              }}
            >
              VE
            </span>
          )}
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>控制点</h2>
          <div className="button-row">
            <button
              className="secondary-button"
              disabled={points.length >= 10}
              onClick={addControlPoint}
              type="button"
            >
              增加点
            </button>
            <button
              className="secondary-button"
              disabled={points.length <= 4}
              onClick={removeLastControlPoint}
              type="button"
            >
              删除末点
            </button>
          </div>
        </div>
        <div className="point-editor-list">
          {points.map((point, index) => (
            <div className={index === activeIndex ? "point-editor active" : "point-editor"} key={index}>
              <strong>{`P${index + 1}`}</strong>
              <span>{`px (${point.pixel_x.toFixed(2)}, ${point.pixel_y.toFixed(2)})`}</span>
              <label>
                <span>X/m</span>
                <input
                  onChange={(event) => updateWorldPoint(index, "world_x", event.target.value)}
                  type="number"
                  value={point.world_x}
                />
              </label>
              <label>
                <span>Y/m</span>
                <input
                  onChange={(event) => updateWorldPoint(index, "world_y", event.target.value)}
                  type="number"
                  value={point.world_y}
                />
              </label>
              <button className="secondary-button" onClick={() => setActiveIndex(index)} type="button">
                选择
              </button>
            </div>
          ))}
        </div>
      </section>

      <section className="panel wide">
        <div className="panel-heading">
          <h2>验证与地面区域</h2>
          <div className="button-row">
            <button
              className="secondary-button"
              disabled={points.length < 4}
              onClick={updateRoadPolygonFromFirstFourPoints}
              type="button"
            >
              前四点生成地面区域
            </button>
            <button
              className="secondary-button"
              onClick={clearRoadPixelPolygon}
              type="button"
            >
              重画像素地面区域
            </button>
          </div>
        </div>
        <div className="validation-builder">
          <label>
            <span>验证段名称</span>
            <input onChange={(event) => setSegmentName(event.target.value)} value={segmentName} />
          </label>
          <label>
            <span>像素起点 u</span>
            <input
              onChange={(event) =>
                updateSegmentTuple(setSegmentPixelStart, segmentPixelStart, 0, event.target.value)
              }
              type="number"
              value={segmentPixelStart[0]}
            />
          </label>
          <label>
            <span>像素起点 v</span>
            <input
              onChange={(event) =>
                updateSegmentTuple(setSegmentPixelStart, segmentPixelStart, 1, event.target.value)
              }
              type="number"
              value={segmentPixelStart[1]}
            />
          </label>
          <label>
            <span>像素终点 u</span>
            <input
              onChange={(event) =>
                updateSegmentTuple(setSegmentPixelEnd, segmentPixelEnd, 0, event.target.value)
              }
              type="number"
              value={segmentPixelEnd[0]}
            />
          </label>
          <label>
            <span>像素终点 v</span>
            <input
              onChange={(event) =>
                updateSegmentTuple(setSegmentPixelEnd, segmentPixelEnd, 1, event.target.value)
              }
              type="number"
              value={segmentPixelEnd[1]}
            />
          </label>
          <label>
            <span>米制起点 X</span>
            <input
              onChange={(event) =>
                updateSegmentTuple(setSegmentWorldStart, segmentWorldStart, 0, event.target.value)
              }
              type="number"
              value={segmentWorldStart[0]}
            />
          </label>
          <label>
            <span>米制起点 Y</span>
            <input
              onChange={(event) =>
                updateSegmentTuple(setSegmentWorldStart, segmentWorldStart, 1, event.target.value)
              }
              type="number"
              value={segmentWorldStart[1]}
            />
          </label>
          <label>
            <span>米制终点 X</span>
            <input
              onChange={(event) =>
                updateSegmentTuple(setSegmentWorldEnd, segmentWorldEnd, 0, event.target.value)
              }
              type="number"
              value={segmentWorldEnd[0]}
            />
          </label>
          <label>
            <span>米制终点 Y</span>
            <input
              onChange={(event) =>
                updateSegmentTuple(setSegmentWorldEnd, segmentWorldEnd, 1, event.target.value)
              }
              type="number"
              value={segmentWorldEnd[1]}
            />
          </label>
          <button className="secondary-button" onClick={addIndependentValidationSegment} type="button">
            添加独立验证段
          </button>
          <button
            className="secondary-button"
            onClick={() => setPickTarget("segment_pixel_start")}
            type="button"
          >
            画面点选像素端点
          </button>
        </div>
        <div className="validation-segment-list">
          {validationSegments.length === 0 ? (
            <span>尚未添加独立验证线段</span>
          ) : (
            validationSegments.map((segment, index) => (
              <div key={`${segment.name}-${index}`}>
                <strong>{segment.name}</strong>
                <span
                  className={
                    isIndependentValidationSegment(points, segment)
                      ? "segment-independence pass"
                      : "segment-independence fail"
                  }
                >
                  {isIndependentValidationSegment(points, segment)
                    ? "独立验证"
                    : "复用控制点"}
                </span>
                <span>{`px (${segment.pixel_start.join(", ")}) -> (${segment.pixel_end.join(", ")})`}</span>
                <span>{`m (${segment.world_start.join(", ")}) -> (${segment.world_end.join(", ")})`}</span>
                <button
                  className="secondary-button"
                  onClick={() => removeValidationSegment(index)}
                  type="button"
                >
                  删除
                </button>
              </div>
            ))
          )}
        </div>
        <div className="calibration-json-grid">
          <label>
            <span>road_plane_polygon_pixel</span>
            <textarea
              onChange={(event) => setRoadPixelPolygonText(event.target.value)}
              value={roadPixelPolygonText}
            />
          </label>
          <label>
            <span>road_plane_polygon_world</span>
            <textarea
              onChange={(event) => setRoadPolygonText(event.target.value)}
              value={roadPolygonText}
            />
          </label>
          <label>
            <span>validation_segments</span>
            <textarea
              onChange={(event) => setValidationSegmentsText(event.target.value)}
              value={validationSegmentsText}
            />
          </label>
        </div>
      </section>

      <section className="panel wide">
        <div className="panel-heading">
          <h2>保存标定</h2>
          <div className="button-row">
            <button
              className="primary-button"
              disabled={isSaving}
              onClick={() => void saveToYaml()}
              type="button"
            >
              {isSaving ? "保存中" : "保存到 YAML"}
            </button>
            <button
              className="secondary-button"
              onClick={() => downloadJson(`${clipName}.calibration-entry.json`, exportPayload)}
              type="button"
            >
              下载片段
            </button>
            <button
              className="secondary-button"
              onClick={() =>
                downloadJson(`${clipName}.golden-calibration-picks.json`, goldenPickerPayload)
              }
              type="button"
            >
              下载采点 JSON
            </button>
            <button
              className="primary-button"
              onClick={() => downloadJson("calibration_presets.generated.json", fullPresetPayload)}
              type="button"
            >
              下载完整 preset
            </button>
          </div>
        </div>
        <div className="calibration-gate-summary">
          <div>
            <span>可信门禁</span>
            <strong>
              {localGateChecks.every((item) => item.passed)
                ? "可提交后端验证"
                : "继续补采"}
            </strong>
          </div>
          {localGateChecks.map((item) => (
            <div className={item.passed ? "gate-check pass" : "gate-check fail"} key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
            </div>
          ))}
        </div>
        {saveError && <p className="task-error">保存失败：{saveError}</p>}
        {saveResult && (
          <div className="calibration-diagnostics">
            <div>
              <span>标定来源</span>
              <strong>{saveResult.source}</strong>
            </div>
            <div>
              <span>质量分级</span>
              <strong>{saveResult.diagnostics.calibration_quality}</strong>
            </div>
            <div>
              <span>world-&gt;pixel RMSE</span>
              <strong>
                {`${(
                  saveResult.diagnostics.world_to_pixel_rmse_px ??
                  saveResult.diagnostics.reprojection_rmse_px
                ).toFixed(3)} px`}
              </strong>
            </div>
            <div>
              <span>pixel-&gt;world RMSE</span>
              <strong>
                {`${(saveResult.diagnostics.pixel_to_world_rmse_m ?? 0).toFixed(3)} m`}
              </strong>
            </div>
            <div>
              <span>验证误差</span>
              <strong>
                {saveResult.diagnostics.validation_max_error_px == null
                  ? "N/A"
                  : `${saveResult.diagnostics.validation_max_error_px.toFixed(3)} px`}
              </strong>
            </div>
            <div>
              <span>独立验证线</span>
              <strong>{saveResult.diagnostics.independent_validation_segment_count ?? 0}</strong>
            </div>
            {savedGateChecks.map((item) => (
              <div className={item.passed ? "gate-check pass" : "gate-check fail"} key={item.label}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
              </div>
            ))}
            <div>
              <span>可信标定</span>
              <strong>{String(saveResult.diagnostics.calibration_trusted ?? false)}</strong>
            </div>
            <div>
              <span>RANSAC 内点</span>
              <strong>{saveResult.diagnostics.inlier_count}</strong>
            </div>
            <div>
              <span>条件数</span>
              <strong>{saveResult.diagnostics.condition_number.toExponential(2)}</strong>
            </div>
            <div>
              <span>YAML 路径</span>
              <strong>{saveResult.preset_path}</strong>
            </div>
            {saveResult.diagnostics.error_sources?.length ? (
              <div className="diagnostic-wide">
                <span>误差/降级来源</span>
                <strong>{saveResult.diagnostics.error_sources.join(" / ")}</strong>
              </div>
            ) : null}
          </div>
        )}
        <pre className="report-output">{JSON.stringify(fullPresetPayload, null, 2)}</pre>
      </section>
    </div>
  );
}
