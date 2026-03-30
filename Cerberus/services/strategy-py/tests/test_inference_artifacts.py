from __future__ import annotations

import json
from pathlib import Path

import torch

from app.infrastructure.inference_artifacts import GcsArtifactLoader, PublicGoogleDriveArtifactLoader


def test_extract_file_id_from_shared_folder_html() -> None:
    html = """
    [[null,"1SKvwWiubco-zxzXBVdQlE0t21mbFXjky"],null,null,null,"application/json",null,null,null,null,null,null,true,null,null,null,[[2]],null,null,null,null,null,null,null,null,[[[""],[null,["application/json"]],null,null,null,"Unknown"],null,[[16,null,[null,[[["artifact_manifest.json",null,true]]]],null,null,[[["artifact_manifest.json",null,true],["Unknown"]]]]]]]
    [[null,"1W9krkFMyZ2oGO9SCBLjwSFQ4GjDiiY0u"],null,null,null,"application/octet-stream",null,null,null,null,null,null,true,null,null,null,[[2]],null,null,null,null,null,null,null,null,[[[""],[null,["application/octet-stream"]],null,null,null,"Binary"],null,[[16,null,[null,[[["cerberus_signal_model.onnx",null,true]]]],null,null,[[["cerberus_signal_model.onnx",null,true],["Binary"]]]]]]]
    """

    manifest_id = PublicGoogleDriveArtifactLoader.extract_file_id_from_html(
        html,
        "artifact_manifest.json",
    )
    onnx_id = PublicGoogleDriveArtifactLoader.extract_file_id_from_html(
        html,
        "cerberus_signal_model.onnx",
    )

    assert manifest_id == "1SKvwWiubco-zxzXBVdQlE0t21mbFXjky"
    assert onnx_id == "1W9krkFMyZ2oGO9SCBLjwSFQ4GjDiiY0u"


def test_load_preprocessing_from_training_bundle(tmp_path: Path) -> None:
    checkpoint_path = tmp_path / "cerberus_signal_model.pt"
    torch.save(
        {
            "feature_columns": ["f1", "f2"],
            "feature_mean": [1.0, 2.0],
            "feature_std": [0.5, 0.25],
            "symbol_to_id": {"BTCUSDT": 0, "ETHUSDT": 1},
            "config": {"lookback": 16},
        },
        checkpoint_path,
    )

    loader = PublicGoogleDriveArtifactLoader(
        folder_url="https://drive.google.com/drive/folders/1Wu4LyNVfm6FSatUVfmA1CiG-2YGDdG7p",
        cache_dir=tmp_path,
    )
    manifest = {"lookback": 8, "symbols": ["BTCUSDT", "ETHUSDT"]}

    preprocessing = loader._load_preprocessing(
        checkpoint_path,
        manifest,
        preprocessing_path=None,
        cache_dir=tmp_path / "1Wu4LyNVfm6FSatUVfmA1CiG-2YGDdG7p",
    )

    assert preprocessing.feature_columns == ("f1", "f2")
    assert preprocessing.feature_mean == (1.0, 2.0)
    assert preprocessing.feature_std == (0.5, 0.25)
    assert preprocessing.symbol_to_id == {"BTCUSDT": 0, "ETHUSDT": 1}
    assert preprocessing.lookback == 16

    cached = json.loads((tmp_path / "1Wu4LyNVfm6FSatUVfmA1CiG-2YGDdG7p" / "preprocessing.json").read_text())
    assert cached["symbol_to_id"] == {"BTCUSDT": 0, "ETHUSDT": 1}


def test_parse_gcs_artifact_uri() -> None:
    location = GcsArtifactLoader.parse_gcs_uri(
        "gs://cerberus-9d94f-models-20260330-ae2/models/cerberus-transformer-lstm/v1/best_model"
    )

    assert location.bucket == "cerberus-9d94f-models-20260330-ae2"
    assert location.prefix == "models/cerberus-transformer-lstm/v1/best_model"
    assert location.cache_key == (
        "cerberus-9d94f-models-20260330-ae2_models_cerberus-transformer-lstm_v1_best_model"
    )


class _FakeBlob:
    def __init__(self, source: Path) -> None:
        self._source = source

    def exists(self) -> bool:
        return self._source.exists()

    def download_to_filename(self, destination: str) -> None:
        Path(destination).write_bytes(self._source.read_bytes())


class _FakeBucket:
    def __init__(self, root: Path) -> None:
        self._root = root

    def blob(self, name: str) -> _FakeBlob:
        return _FakeBlob(self._root / name)


class _FakeStorageClient:
    def __init__(self, root: Path) -> None:
        self._root = root

    def bucket(self, _name: str) -> _FakeBucket:
        return _FakeBucket(self._root)


def test_load_gcs_artifacts_and_preprocessing(tmp_path: Path) -> None:
    artifact_root = tmp_path / "remote"
    artifact_prefix = artifact_root / "models" / "cerberus-transformer-lstm" / "v1" / "best_model"
    artifact_prefix.mkdir(parents=True)

    manifest = {
        "lookback": 8,
        "symbols": ["BTCUSDT", "ETHUSDT"],
        "feature_columns": ["f1", "f2"],
    }
    metrics = {"best_macro_f1": 0.5}
    (artifact_prefix / "artifact_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (artifact_prefix / "training_metrics.json").write_text(json.dumps(metrics), encoding="utf-8")
    (artifact_prefix / "cerberus_signal_model.onnx").write_bytes(b"onnx")
    torch.save(
        {
            "feature_columns": ["f1", "f2"],
            "feature_mean": [1.0, 2.0],
            "feature_std": [0.5, 0.25],
            "symbol_to_id": {"BTCUSDT": 0, "ETHUSDT": 1},
            "config": {"lookback": 16},
        },
        artifact_prefix / "cerberus_signal_model.pt",
    )

    loader = GcsArtifactLoader(
        gcs_uri="gs://cerberus-9d94f-models-20260330-ae2/models/cerberus-transformer-lstm/v1/best_model",
        cache_dir=tmp_path / "cache",
        client=_FakeStorageClient(artifact_root),
    )

    loaded = loader.load()

    assert loaded.manifest["symbols"] == ["BTCUSDT", "ETHUSDT"]
    assert loaded.metrics["best_macro_f1"] == 0.5
    assert loaded.preprocessing.symbol_to_id == {"BTCUSDT": 0, "ETHUSDT": 1}
    assert loaded.preprocessing.lookback == 16
    assert loaded.onnx_path.exists()
    assert loaded.training_bundle_path.exists()


def test_load_gcs_artifacts_prefers_preprocessing_json(tmp_path: Path) -> None:
    artifact_root = tmp_path / "remote"
    artifact_prefix = artifact_root / "models" / "cerberus-transformer-lstm" / "v1" / "best_model"
    artifact_prefix.mkdir(parents=True)

    manifest = {
        "lookback": 8,
        "symbols": ["BTCUSDT"],
        "feature_columns": ["f1", "f2"],
    }
    metrics = {"best_macro_f1": 0.5}
    preprocessing = {
        "feature_columns": ["f1", "f2"],
        "feature_mean": [1.0, 2.0],
        "feature_std": [0.5, 0.25],
        "symbol_to_id": {"BTCUSDT": 0},
        "lookback": 16,
    }
    (artifact_prefix / "artifact_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (artifact_prefix / "training_metrics.json").write_text(json.dumps(metrics), encoding="utf-8")
    (artifact_prefix / "preprocessing.json").write_text(json.dumps(preprocessing), encoding="utf-8")
    (artifact_prefix / "cerberus_signal_model.onnx").write_bytes(b"onnx")

    loader = GcsArtifactLoader(
        gcs_uri="gs://cerberus-9d94f-models-20260330-ae2/models/cerberus-transformer-lstm/v1/best_model",
        cache_dir=tmp_path / "cache",
        client=_FakeStorageClient(artifact_root),
    )

    loaded = loader.load()

    assert loaded.preprocessing.symbol_to_id == {"BTCUSDT": 0}
    assert loaded.preprocessing.lookback == 16
    assert loaded.training_bundle_path is None
