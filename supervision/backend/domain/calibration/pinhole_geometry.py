from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from domain.calibration.models import HomographyResult, MetricPlaneCalibration
from domain.speed.view_transformer import ViewTransformer


@dataclass(frozen=True)
class PinholeGeometryAudit:
    intrinsics: list[list[float]] | None
    extrinsics: dict[str, object] | None
    camera_height_m: float | None
    tilt_rad: float | None
    roll_rad: float | None
    ground_plane_normal: list[float] | None
    homography_decomposition_residual: float | None
    local_jacobian_speed_amplification_p95: float | None
    local_jacobian_condition_p95: float | None
    intrinsics_consistency_status: str
    model_reference: str = "pinhole_geometry_audit_v1"

    def to_diagnostics(self) -> dict[str, object]:
        return {
            "intrinsics": self.intrinsics,
            "extrinsics": self.extrinsics,
            "camera_height_m": self.camera_height_m,
            "tilt_rad": self.tilt_rad,
            "roll_rad": self.roll_rad,
            "ground_plane_normal": self.ground_plane_normal,
            "homography_decomposition_residual": self.homography_decomposition_residual,
            "local_jacobian_speed_amplification_p95": (
                self.local_jacobian_speed_amplification_p95
            ),
            "local_jacobian_condition_p95": self.local_jacobian_condition_p95,
            "intrinsics_consistency_status": self.intrinsics_consistency_status,
            "model_reference": self.model_reference,
        }


class PinholeGeometryAuditor:
    """Audit whether a planar homography is compatible with a pinhole profile."""

    def audit(
        self,
        calibration: HomographyResult,
        metric_planes: list[MetricPlaneCalibration],
        calibration_context: dict[str, object],
        *,
        frame_width: int,
        frame_height: int,
    ) -> PinholeGeometryAudit:
        intrinsics = _matrix3(
            calibration_context.get("camera_matrix_used"),
        ) or _matrix3(calibration_context.get("camera_intrinsics"))
        extrinsics = _dict_or_none(calibration_context.get("camera_extrinsics"))
        camera_height = _optional_float(calibration_context.get("camera_height_m"))
        tilt = _optional_float(calibration_context.get("tilt_rad"))
        roll = _optional_float(calibration_context.get("roll_rad"))
        ground_normal = _vector3(calibration_context.get("ground_plane_normal"))
        residual = self._decomposition_residual(calibration, intrinsics)
        amplification_p95, condition_p95 = self._jacobian_stats(
            calibration,
            frame_width=frame_width,
            frame_height=frame_height,
        )
        return PinholeGeometryAudit(
            intrinsics=intrinsics,
            extrinsics=extrinsics,
            camera_height_m=camera_height,
            tilt_rad=tilt,
            roll_rad=roll,
            ground_plane_normal=ground_normal,
            homography_decomposition_residual=residual,
            local_jacobian_speed_amplification_p95=amplification_p95,
            local_jacobian_condition_p95=condition_p95,
            intrinsics_consistency_status=self._intrinsics_consistency(
                intrinsics,
                metric_planes,
            ),
        )

    @staticmethod
    def _decomposition_residual(
        calibration: HomographyResult,
        intrinsics: list[list[float]] | None,
    ) -> float | None:
        if intrinsics is None:
            return None
        try:
            camera_matrix = np.asarray(intrinsics, dtype=np.float64)
            homography = np.asarray(calibration.homography_matrix, dtype=np.float64)
            normalized = np.linalg.pinv(camera_matrix) @ homography
            h1 = normalized[:, 0]
            h2 = normalized[:, 1]
            norm1 = np.linalg.norm(h1)
            norm2 = np.linalg.norm(h2)
            if norm1 <= 1e-9 or norm2 <= 1e-9:
                return None
            unit1 = h1 / norm1
            unit2 = h2 / norm2
            orthogonality = abs(float(unit1 @ unit2))
            scale_mismatch = abs(norm1 - norm2) / max((norm1 + norm2) / 2.0, 1e-9)
            return float(orthogonality + scale_mismatch)
        except (ValueError, np.linalg.LinAlgError):
            return None

    @staticmethod
    def _jacobian_stats(
        calibration: HomographyResult,
        *,
        frame_width: int,
        frame_height: int,
    ) -> tuple[float | None, float | None]:
        transformer = ViewTransformer(calibration.homography_matrix)
        xs = np.linspace(frame_width * 0.15, frame_width * 0.85, 5)
        ys = np.linspace(frame_height * 0.15, frame_height * 0.95, 5)
        amplifications: list[float] = []
        conditions: list[float] = []
        for x in xs:
            for y in ys:
                try:
                    jacobian = transformer.local_jacobian(float(x), float(y))
                except (ValueError, ZeroDivisionError, np.linalg.LinAlgError):
                    continue
                if jacobian.shape != (2, 2) or not np.all(np.isfinite(jacobian)):
                    continue
                singular_values = np.linalg.svd(jacobian, compute_uv=False)
                if singular_values.size != 2:
                    continue
                amplifications.append(float(max(singular_values)))
                conditions.append(float(max(singular_values) / max(min(singular_values), 1e-9)))
        if not amplifications:
            return None, None
        return (
            float(np.percentile(amplifications, 95)),
            float(np.percentile(conditions, 95)),
        )

    @staticmethod
    def _intrinsics_consistency(
        intrinsics: list[list[float]] | None,
        metric_planes: list[MetricPlaneCalibration],
    ) -> str:
        if intrinsics is None:
            return "intrinsics_unverified"
        trusted = [plane for plane in metric_planes if plane.trusted]
        if len(trusted) <= 1:
            return "single_plane"
        condition_numbers = [
            float(plane.homography.condition_number)
            for plane in trusted
            if np.isfinite(plane.homography.condition_number)
        ]
        if not condition_numbers:
            return "insufficient_plane_evidence"
        spread = max(condition_numbers) / max(min(condition_numbers), 1e-9)
        return "intrinsics_inconsistent_across_planes" if spread > 25.0 else "consistent"


def _matrix3(value: object) -> list[list[float]] | None:
    if isinstance(value, dict):
        try:
            fx = float(value["fx"])
            fy = float(value["fy"])
            cx = float(value["cx"])
            cy = float(value["cy"])
        except (KeyError, TypeError, ValueError):
            return None
        return [[fx, 0.0, cx], [0.0, fy, cy], [0.0, 0.0, 1.0]]
    if not isinstance(value, list) or len(value) != 3:
        return None
    matrix: list[list[float]] = []
    for row in value:
        if not isinstance(row, list) or len(row) != 3:
            return None
        try:
            matrix.append([float(item) for item in row])
        except (TypeError, ValueError):
            return None
    return matrix


def _vector3(value: object) -> list[float] | None:
    if not isinstance(value, list) or len(value) != 3:
        return None
    try:
        return [float(item) for item in value]
    except (TypeError, ValueError):
        return None


def _dict_or_none(value: object) -> dict[str, object] | None:
    return dict(value) if isinstance(value, dict) else None


def _optional_float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
