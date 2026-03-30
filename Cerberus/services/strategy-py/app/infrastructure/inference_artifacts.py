from __future__ import annotations

from dataclasses import dataclass
from html import unescape
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlencode, urljoin

import httpx


@dataclass(frozen=True, slots=True)
class InferencePreprocessing:
    feature_columns: tuple[str, ...]
    feature_mean: tuple[float, ...]
    feature_std: tuple[float, ...]
    symbol_to_id: dict[str, int]
    lookback: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_columns": list(self.feature_columns),
            "feature_mean": list(self.feature_mean),
            "feature_std": list(self.feature_std),
            "symbol_to_id": dict(self.symbol_to_id),
            "lookback": self.lookback,
        }


@dataclass(frozen=True, slots=True)
class LoadedInferenceArtifacts:
    manifest: dict[str, Any]
    metrics: dict[str, Any]
    preprocessing: InferencePreprocessing
    onnx_path: Path
    training_bundle_path: Path | None
    cache_dir: Path


class ArtifactLoader:
    @staticmethod
    def _preprocessing_cache_path(cache_dir: Path) -> Path:
        return cache_dir / "preprocessing.json"

    @staticmethod
    def _read_preprocessing_payload(preprocessing_path: Path) -> InferencePreprocessing:
        payload = json.loads(preprocessing_path.read_text(encoding="utf-8"))
        return InferencePreprocessing(
            feature_columns=tuple(payload["feature_columns"]),
            feature_mean=tuple(float(value) for value in payload["feature_mean"]),
            feature_std=tuple(float(value) for value in payload["feature_std"]),
            symbol_to_id={str(key): int(value) for key, value in payload["symbol_to_id"].items()},
            lookback=int(payload["lookback"]),
        )

    def _load_preprocessing(
        self,
        training_bundle_path: Path | None,
        manifest: dict[str, Any],
        *,
        preprocessing_path: Path | None,
        cache_dir: Path,
    ) -> InferencePreprocessing:
        cache_path = self._preprocessing_cache_path(cache_dir)
        if cache_path.exists():
            return self._read_preprocessing_payload(cache_path)

        if preprocessing_path is not None and preprocessing_path.exists():
            preprocessing = self._read_preprocessing_payload(preprocessing_path)
            if preprocessing_path != cache_path:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(
                    json.dumps(preprocessing.to_dict(), indent=2),
                    encoding="utf-8",
                )
            return preprocessing

        if training_bundle_path is None:
            raise FileNotFoundError("missing preprocessing.json and cerberus_signal_model.pt")
        checkpoint = self._load_training_bundle(training_bundle_path)
        symbol_to_id = checkpoint.get("symbol_to_id") or self._build_symbol_to_id_from_manifest(manifest)
        preprocessing = InferencePreprocessing(
            feature_columns=tuple(str(item) for item in checkpoint["feature_columns"]),
            feature_mean=tuple(float(value) for value in checkpoint["feature_mean"]),
            feature_std=tuple(float(value) for value in checkpoint["feature_std"]),
            symbol_to_id={str(key): int(value) for key, value in symbol_to_id.items()},
            lookback=int(checkpoint.get("config", {}).get("lookback", manifest["lookback"])),
        )
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(preprocessing.to_dict(), indent=2), encoding="utf-8")
        return preprocessing

    @staticmethod
    def _build_symbol_to_id_from_manifest(manifest: dict[str, Any]) -> dict[str, int]:
        symbols = [str(item) for item in manifest.get("symbols", [])]
        return {symbol: index for index, symbol in enumerate(sorted(symbols))}

    @staticmethod
    def _load_training_bundle(training_bundle_path: Path) -> dict[str, Any]:
        try:
            import torch
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "torch is not installed; provide preprocessing.json with the inference artifacts "
                "or install torch to read legacy cerberus_signal_model.pt bundles"
            ) from exc

        loaded = torch.load(training_bundle_path, map_location="cpu", weights_only=False)
        if not isinstance(loaded, dict):
            raise TypeError("training bundle must be a checkpoint dictionary")
        return loaded


class PublicGoogleDriveArtifactLoader(ArtifactLoader):
    _GOOGLE_DRIVE_BASE = "https://drive.google.com"
    _DEFAULT_TIMEOUT_SECONDS = 60.0
    _FILE_ID_PATTERN = re.compile(r'\[null,"([A-Za-z0-9_-]{20,})"\],null,null,null,"[^"]+"')

    def __init__(
        self,
        *,
        folder_url: str,
        cache_dir: str | Path,
        client: httpx.Client | None = None,
    ) -> None:
        self._folder_url = folder_url
        self._folder_id = self._extract_folder_id(folder_url)
        self._cache_dir = Path(cache_dir) / self._folder_id
        self._client = client or httpx.Client(
            follow_redirects=True,
            timeout=self._DEFAULT_TIMEOUT_SECONDS,
            headers={"user-agent": "cerberus-strategy/0.1.0"},
        )

    def load(self) -> LoadedInferenceArtifacts:
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        folder_html = self._fetch_folder_page()
        file_ids = self._extract_required_file_ids(folder_html)

        manifest_path = self._download_artifact(file_ids["artifact_manifest.json"], "artifact_manifest.json")
        metrics_path = self._download_artifact(file_ids["training_metrics.json"], "training_metrics.json")
        onnx_path = self._download_artifact(
            file_ids["cerberus_signal_model.onnx"],
            "cerberus_signal_model.onnx",
        )
        preprocessing_path = self._download_optional_artifact(
            file_ids.get("preprocessing.json"),
            "preprocessing.json",
        )
        bundle_path = None
        if preprocessing_path is None:
            bundle_path = self._download_artifact(
                file_ids["cerberus_signal_model.pt"],
                "cerberus_signal_model.pt",
            )

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        preprocessing = self._load_preprocessing(
            bundle_path,
            manifest,
            preprocessing_path=preprocessing_path,
            cache_dir=self._cache_dir,
        )

        return LoadedInferenceArtifacts(
            manifest=manifest,
            metrics=metrics,
            preprocessing=preprocessing,
            onnx_path=onnx_path,
            training_bundle_path=bundle_path,
            cache_dir=self._cache_dir,
        )

    @classmethod
    def _extract_folder_id(cls, folder_url: str) -> str:
        match = re.search(r"/folders/([A-Za-z0-9_-]+)", folder_url)
        if match is None:
            raise ValueError("unsupported Google Drive folder URL")
        return match.group(1)

    @classmethod
    def extract_file_id_from_html(cls, html: str, filename: str) -> str:
        document = unescape(html)
        index = document.find(filename)
        if index < 0:
            raise FileNotFoundError(f"unable to locate '{filename}' in shared folder")
        segment = document[max(0, index - 2000) : index]
        matches = cls._FILE_ID_PATTERN.findall(segment)
        if not matches:
            raise FileNotFoundError(f"unable to resolve file id for '{filename}'")
        return matches[-1]

    def _fetch_folder_page(self) -> str:
        response = self._client.get(self._folder_url)
        response.raise_for_status()
        return response.text

    def _extract_required_file_ids(self, html: str) -> dict[str, str]:
        required_names = (
            "artifact_manifest.json",
            "training_metrics.json",
            "cerberus_signal_model.onnx",
        )
        file_ids = {name: self.extract_file_id_from_html(html, name) for name in required_names}
        file_ids["preprocessing.json"] = self.extract_optional_file_id_from_html(html, "preprocessing.json")
        if file_ids["preprocessing.json"] is None:
            file_ids["cerberus_signal_model.pt"] = self.extract_file_id_from_html(
                html,
                "cerberus_signal_model.pt",
            )
        return file_ids

    @classmethod
    def extract_optional_file_id_from_html(cls, html: str, filename: str) -> str | None:
        try:
            return cls.extract_file_id_from_html(html, filename)
        except FileNotFoundError:
            return None

    def _download_artifact(self, file_id: str, filename: str) -> Path:
        destination = self._cache_dir / filename
        if destination.exists() and destination.stat().st_size > 0:
            return destination

        response = self._client.get(
            f"{self._GOOGLE_DRIVE_BASE}/uc",
            params={"export": "download", "id": file_id},
        )
        response.raise_for_status()
        payload = response.content
        content_type = (response.headers.get("content-type") or "").lower()
        if "text/html" in content_type:
            confirm_url = self._extract_confirm_download_url(response.text)
            if confirm_url is None:
                raise RuntimeError(f"failed to resolve download URL for {filename}")
            response = self._client.get(confirm_url)
            response.raise_for_status()
            payload = response.content

        destination.write_bytes(payload)
        return destination

    def _download_optional_artifact(self, file_id: str | None, filename: str) -> Path | None:
        if file_id is None:
            return None
        return self._download_artifact(file_id, filename)

    def _extract_confirm_download_url(self, html: str) -> str | None:
        form_match = re.search(r'<form[^>]+action="([^"]+)"[^>]*>(.*?)</form>', html, re.S)
        if form_match is not None:
            action = form_match.group(1)
            inputs = re.findall(
                r'<input[^>]+type="hidden"[^>]+name="([^"]+)"[^>]+value="([^"]*)"',
                form_match.group(2),
            )
            if inputs:
                return f"{action}?{urlencode([(name, value) for name, value in inputs])}"
        match = re.search(r'href="(/uc\?export=download[^"]+)"', html)
        if match is not None:
            return urljoin(self._GOOGLE_DRIVE_BASE, unescape(match.group(1)))
        match = re.search(r'"downloadUrl":"([^"]+)"', html)
        if match is not None:
            encoded = match.group(1).replace("\\u003d", "=").replace("\\u0026", "&")
            return encoded.replace("\\/", "/")
        return None

@dataclass(frozen=True, slots=True)
class GcsArtifactLocation:
    bucket: str
    prefix: str
    cache_key: str


class GcsArtifactLoader(ArtifactLoader):
    def __init__(
        self,
        *,
        gcs_uri: str,
        cache_dir: str | Path,
        client: Any | None = None,
    ) -> None:
        self._location = self.parse_gcs_uri(gcs_uri)
        self._cache_dir = Path(cache_dir) / self._location.cache_key
        self._client = client

    def load(self) -> LoadedInferenceArtifacts:
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        client = self._client or self._create_client()
        bucket = client.bucket(self._location.bucket)

        manifest_path = self._download_artifact(bucket, "artifact_manifest.json")
        metrics_path = self._download_artifact(bucket, "training_metrics.json")
        onnx_path = self._download_artifact(bucket, "cerberus_signal_model.onnx")
        preprocessing_path = self._download_optional_artifact(bucket, "preprocessing.json")
        bundle_path = None
        if preprocessing_path is None:
            bundle_path = self._download_artifact(bucket, "cerberus_signal_model.pt")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        preprocessing = self._load_preprocessing(
            bundle_path,
            manifest,
            preprocessing_path=preprocessing_path,
            cache_dir=self._cache_dir,
        )

        return LoadedInferenceArtifacts(
            manifest=manifest,
            metrics=metrics,
            preprocessing=preprocessing,
            onnx_path=onnx_path,
            training_bundle_path=bundle_path,
            cache_dir=self._cache_dir,
        )

    @staticmethod
    def parse_gcs_uri(gcs_uri: str) -> GcsArtifactLocation:
        if not gcs_uri.startswith("gs://"):
            raise ValueError("GCS artifact URI must start with gs://")
        without_scheme = gcs_uri.removeprefix("gs://")
        bucket, _, prefix = without_scheme.partition("/")
        normalized_prefix = prefix.strip("/")
        if not bucket:
            raise ValueError("GCS artifact URI must include a bucket name")
        if not normalized_prefix:
            raise ValueError("GCS artifact URI must include an object prefix")
        return GcsArtifactLocation(
            bucket=bucket,
            prefix=normalized_prefix,
            cache_key=f"{bucket}_{normalized_prefix.replace('/', '_')}",
        )

    def _download_artifact(self, bucket: Any, filename: str) -> Path:
        destination = self._cache_dir / filename
        if destination.exists() and destination.stat().st_size > 0:
            return destination
        blob = bucket.blob(f"{self._location.prefix}/{filename}")
        if not blob.exists():
            raise FileNotFoundError(f"missing GCS inference artifact: {filename}")
        blob.download_to_filename(str(destination))
        return destination

    def _download_optional_artifact(self, bucket: Any, filename: str) -> Path | None:
        destination = self._cache_dir / filename
        if destination.exists() and destination.stat().st_size > 0:
            return destination
        blob = bucket.blob(f"{self._location.prefix}/{filename}")
        if not blob.exists():
            return None
        blob.download_to_filename(str(destination))
        return destination

    @staticmethod
    def _create_client() -> Any:
        from google.cloud import storage

        return storage.Client()
