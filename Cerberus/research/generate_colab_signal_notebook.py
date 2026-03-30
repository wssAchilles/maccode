from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent


def md_cell(source: str) -> dict[str, object]:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": source.splitlines(keepends=True),
    }


def code_cell(source: str) -> dict[str, object]:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.splitlines(keepends=True),
    }


cells = [
    md_cell(
        dedent(
            """
            # Cerberus Colab Signal Training

            这个 notebook 只面向 **Colab 云端训练**。目标是训练一个和 Cerberus 线上契约兼容的三分类模型：

            - `SELL`
            - `HOLD`
            - `BUY`

            产物会导出到 Google Drive，并包含：

            - `cerberus_signal_model.pt`
            - `cerberus_signal_model.onnx`
            - `preprocessing.json`
            - `artifact_manifest.json`
            - `training_metrics.json`

            后续把导出的 **Google Drive 可访问链接** 给我，我就能继续基于这个产物优化模型或对接线上推理。
            """
        ).strip()
    ),
    code_cell(
        dedent(
            """
            !pip -q install --upgrade polars pyarrow pandas numpy scikit-learn torch safetensors tqdm onnx
            """
        ).strip()
    ),
    code_cell(
        dedent(
            """
            from __future__ import annotations

            import gc
            import json
            import math
            import os
            import random
            from dataclasses import asdict, dataclass
            from pathlib import Path
            from typing import Iterable

            import numpy as np
            import pandas as pd
            import polars as pl
            import torch
            import torch.nn as nn
            import torch.nn.functional as F
            from google.colab import drive
            from sklearn.metrics import accuracy_score, classification_report, f1_score
            from torch.utils.data import DataLoader, Dataset
            from tqdm.auto import tqdm

            drive.mount("/content/drive")

            @dataclass
            class TrainConfig:
                drive_data_dir: str = "/content/drive/MyDrive/cerberus/data"
                drive_artifact_dir: str = "/content/drive/MyDrive/cerberus/artifacts"
                run_name: str = "cerberus_signal_transformer_lstm"
                max_files: int | None = None
                target_symbols: tuple[str, ...] = ()
                lookback: int = 256
                horizon: int = 32
                up_threshold_bps: float = 8.0
                down_threshold_bps: float = -8.0
                batch_size: int = 8192
                eval_batch_size: int = 16384
                epochs: int = 10
                learning_rate: float = 3e-4
                weight_decay: float = 1e-2
                grad_clip_norm: float = 1.0
                train_split_ratio: float = 0.8
                num_workers: int = 8
                seed: int = 42
                d_model: int = 512
                nhead: int = 8
                transformer_layers: int = 8
                ff_dim: int = 2048
                lstm_hidden: int = 512
                lstm_layers: int = 3
                symbol_embedding_dim: int = 32
                dropout: float = 0.15
                label_smoothing: float = 0.02
                amp: bool = True
                model_id: str = "cerberus-transformer-lstm"
                model_version: str = "v1"
                model_source: str = "colab"
                strategy_id: str = "inference"

            CFG = TrainConfig()

            torch.manual_seed(CFG.seed)
            np.random.seed(CFG.seed)
            random.seed(CFG.seed)
            torch.set_float32_matmul_precision("high")
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True

            DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            LABEL_TO_SIGNAL = {0: "SELL", 1: "HOLD", 2: "BUY"}
            SIGNAL_TO_LABEL = {value: key for key, value in LABEL_TO_SIGNAL.items()}

            print("device:", DEVICE)
            print("config:", asdict(CFG))
            """
        ).strip()
    ),
    code_cell(
        dedent(
            """
            TIMESTAMP_CANDIDATES = ["event_time", "timestamp", "ts", "time", "datetime", "date"]
            SYMBOL_CANDIDATES = ["symbol", "ticker", "asset"]
            PRICE_CANDIDATES = ["price", "close", "last", "mid_price", "mark_price"]
            QUANTITY_CANDIDATES = ["quantity", "qty", "size", "volume"]
            BID_CANDIDATES = ["best_bid", "bid", "bid_price"]
            ASK_CANDIDATES = ["best_ask", "ask", "ask_price"]

            def _resolve_column(columns: list[str], candidates: list[str]) -> str | None:
                lowered = {column.lower(): column for column in columns}
                for candidate in candidates:
                    if candidate.lower() in lowered:
                        return lowered[candidate.lower()]
                return None

            def _iter_data_files(root: Path) -> list[Path]:
                patterns = ["**/*.parquet", "**/*.pq", "**/*.feather", "**/*.csv"]
                files: list[Path] = []
                for pattern in patterns:
                    files.extend(root.glob(pattern))
                files = sorted({path.resolve() for path in files})
                if CFG.max_files is not None:
                    files = files[: CFG.max_files]
                return files

            def _read_frame(path: Path) -> pl.DataFrame:
                if path.suffix.lower() in {".parquet", ".pq"}:
                    return pl.read_parquet(path)
                if path.suffix.lower() == ".feather":
                    return pl.read_ipc(path)
                return pl.read_csv(path)

            def canonicalize_frame(frame: pl.DataFrame, default_symbol: str = "UNKNOWN") -> pl.DataFrame:
                columns = frame.columns
                ts_col = _resolve_column(columns, TIMESTAMP_CANDIDATES)
                price_col = _resolve_column(columns, PRICE_CANDIDATES)
                qty_col = _resolve_column(columns, QUANTITY_CANDIDATES)
                symbol_col = _resolve_column(columns, SYMBOL_CANDIDATES)
                bid_col = _resolve_column(columns, BID_CANDIDATES)
                ask_col = _resolve_column(columns, ASK_CANDIDATES)

                if ts_col is None or price_col is None:
                    raise ValueError(f"frame missing required columns: timestamp={ts_col}, price={price_col}")

                out = frame.with_columns([
                    pl.col(ts_col).alias("event_time_raw"),
                    pl.col(price_col).cast(pl.Float64).alias("price"),
                    (pl.col(qty_col).cast(pl.Float64) if qty_col else pl.lit(0.0)).alias("quantity"),
                    (pl.col(symbol_col).cast(pl.Utf8) if symbol_col else pl.lit(default_symbol)).alias("symbol"),
                    (pl.col(bid_col).cast(pl.Float64) if bid_col else pl.lit(None)).alias("best_bid"),
                    (pl.col(ask_col).cast(pl.Float64) if ask_col else pl.lit(None)).alias("best_ask"),
                ])

                out = out.with_columns(
                    pl.when(pl.col("event_time_raw").cast(pl.Utf8).str.contains(r"^\\d+$"))
                    .then(pl.from_epoch(pl.col("event_time_raw").cast(pl.Int64), time_unit="ms"))
                    .otherwise(pl.col("event_time_raw").str.to_datetime(strict=False))
                    .alias("event_time")
                )

                out = out.filter(pl.col("event_time").is_not_null() & pl.col("price").is_not_null())
                out = out.sort(["symbol", "event_time"])
                return out.select(["symbol", "event_time", "price", "quantity", "best_bid", "best_ask"])

            def load_market_history(data_dir: str) -> pl.DataFrame:
                root = Path(data_dir)
                files = _iter_data_files(root)
                if not files:
                    raise FileNotFoundError(f"no input files found under {root}")
                print(f"loading {len(files)} files from {root}")
                frames = []
                for path in tqdm(files):
                    frame = canonicalize_frame(_read_frame(path), default_symbol=path.stem.split("_")[0].upper())
                    frames.append(frame)
                combined = pl.concat(frames, how="vertical_relaxed")
                if CFG.target_symbols:
                    combined = combined.filter(pl.col("symbol").is_in(list(CFG.target_symbols)))
                combined = combined.sort(["symbol", "event_time"])
                print(combined.head())
                print("rows:", combined.height)
                print("symbols:", combined.select(pl.col("symbol").n_unique()).item())
                return combined

            raw_df = load_market_history(CFG.drive_data_dir)
            """
        ).strip()
    ),
    code_cell(
        dedent(
            """
            def engineer_features(frame: pl.DataFrame) -> tuple[pd.DataFrame, list[str]]:
                lazy = frame.lazy().with_columns([
                    pl.col("price").log().diff().over("symbol").alias("log_ret_1"),
                    pl.col("price").pct_change().over("symbol").alias("ret_1"),
                    pl.col("price").pct_change(3).over("symbol").alias("ret_3"),
                    pl.col("price").pct_change(8).over("symbol").alias("ret_8"),
                    pl.col("price").pct_change(21).over("symbol").alias("ret_21"),
                    pl.col("quantity").log1p().alias("log_quantity"),
                    pl.col("price").ewm_mean(span=8).over("symbol").alias("ema_8"),
                    pl.col("price").ewm_mean(span=21).over("symbol").alias("ema_21"),
                    pl.col("price").ewm_mean(span=55).over("symbol").alias("ema_55"),
                    pl.col("price").rolling_std(window_size=8).over("symbol").alias("vol_8"),
                    pl.col("price").rolling_std(window_size=21).over("symbol").alias("vol_21"),
                    pl.col("quantity").rolling_mean(window_size=21).over("symbol").alias("qty_mean_21"),
                    pl.col("quantity").rolling_std(window_size=21).over("symbol").alias("qty_std_21"),
                    ((pl.col("best_ask") - pl.col("best_bid")) / pl.col("price") * 10000.0).alias("spread_bps"),
                    (((pl.col("best_bid") + pl.col("best_ask")) / 2.0) / pl.col("price") - 1.0).alias("mid_vs_last"),
                ]).with_columns([
                    ((pl.col("price") - pl.col("ema_8")) / pl.col("ema_8")).alias("ema_gap_8"),
                    ((pl.col("price") - pl.col("ema_21")) / pl.col("ema_21")).alias("ema_gap_21"),
                    ((pl.col("ema_8") - pl.col("ema_21")) / pl.col("ema_21")).alias("ema_cross_8_21"),
                    ((pl.col("ema_21") - pl.col("ema_55")) / pl.col("ema_55")).alias("ema_cross_21_55"),
                    ((pl.col("quantity") - pl.col("qty_mean_21")) / (pl.col("qty_std_21") + 1e-6)).alias("qty_z_21"),
                    (pl.col("price") * pl.col("quantity")).alias("notional"),
                ]).with_columns([
                    pl.col("notional").rolling_mean(window_size=21).over("symbol").alias("notional_mean_21"),
                    pl.col("notional").rolling_std(window_size=21).over("symbol").alias("notional_std_21"),
                    (pl.col("price").shift(-CFG.horizon).over("symbol") / pl.col("price") - 1.0).alias("future_return"),
                ]).with_columns([
                    ((pl.col("notional") - pl.col("notional_mean_21")) / (pl.col("notional_std_21") + 1e-6)).alias("notional_z_21"),
                    pl.when(pl.col("future_return") * 10000.0 >= CFG.up_threshold_bps)
                    .then(pl.lit(2))
                    .when(pl.col("future_return") * 10000.0 <= CFG.down_threshold_bps)
                    .then(pl.lit(0))
                    .otherwise(pl.lit(1))
                    .alias("label"),
                ])

                feature_columns = [
                    "log_ret_1",
                    "ret_1",
                    "ret_3",
                    "ret_8",
                    "ret_21",
                    "log_quantity",
                    "ema_gap_8",
                    "ema_gap_21",
                    "ema_cross_8_21",
                    "ema_cross_21_55",
                    "vol_8",
                    "vol_21",
                    "qty_z_21",
                    "spread_bps",
                    "mid_vs_last",
                    "notional_z_21",
                ]

                out = lazy.collect().drop_nulls(subset=feature_columns + ["label", "future_return"])
                pdf = out.select(["symbol", "event_time", *feature_columns, "label", "future_return"]).to_pandas()
                pdf["event_time"] = pd.to_datetime(pdf["event_time"], utc=True)
                return pdf, feature_columns

            feature_df, FEATURE_COLUMNS = engineer_features(raw_df)
            print(feature_df.head())
            print("feature columns:", FEATURE_COLUMNS)
            del raw_df
            gc.collect()
            print("label distribution:", feature_df["label"].value_counts().to_dict())
            """
        ).strip()
    ),
    code_cell(
        dedent(
            """
            class GroupedSequenceDataset(Dataset):
                def __init__(
                    self,
                    *,
                    frames_by_symbol: dict[str, pd.DataFrame],
                    feature_columns: list[str],
                    lookback: int,
                    symbol_to_id: dict[str, int],
                ) -> None:
                    self.feature_columns = feature_columns
                    self.lookback = lookback
                    self.samples: list[tuple[str, int]] = []
                    self.features: dict[str, np.ndarray] = {}
                    self.labels: dict[str, np.ndarray] = {}
                    self.symbol_to_id = symbol_to_id

                    for symbol, frame in frames_by_symbol.items():
                        values = frame[feature_columns].to_numpy(dtype=np.float32)
                        labels = frame["label"].to_numpy(dtype=np.int64)
                        self.features[symbol] = values
                        self.labels[symbol] = labels
                        for end_idx in range(lookback, len(frame)):
                            self.samples.append((symbol, end_idx))

                def __len__(self) -> int:
                    return len(self.samples)

                def __getitem__(self, index: int):
                    symbol, end_idx = self.samples[index]
                    start_idx = end_idx - self.lookback
                    x = self.features[symbol][start_idx:end_idx]
                    y = self.labels[symbol][end_idx]
                    return (
                        torch.from_numpy(x),
                        torch.tensor(self.symbol_to_id[symbol], dtype=torch.long),
                        torch.tensor(y, dtype=torch.long),
                    )

            class CerberusSequenceClassifier(nn.Module):
                def __init__(
                    self,
                    *,
                    feature_dim: int,
                    num_symbols: int,
                    lookback: int,
                    d_model: int,
                    nhead: int,
                    transformer_layers: int,
                    ff_dim: int,
                    lstm_hidden: int,
                    lstm_layers: int,
                    symbol_embedding_dim: int,
                    dropout: float,
                ) -> None:
                    super().__init__()
                    self.input_norm = nn.LayerNorm(feature_dim)
                    self.input_proj = nn.Linear(feature_dim, d_model)
                    self.position = nn.Parameter(torch.randn(1, lookback, d_model) * 0.02)
                    encoder_layer = nn.TransformerEncoderLayer(
                        d_model=d_model,
                        nhead=nhead,
                        dim_feedforward=ff_dim,
                        dropout=dropout,
                        activation="gelu",
                        batch_first=True,
                        norm_first=True,
                    )
                    self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=transformer_layers)
                    self.lstm = nn.LSTM(
                        input_size=d_model,
                        hidden_size=lstm_hidden,
                        num_layers=lstm_layers,
                        batch_first=True,
                        dropout=dropout if lstm_layers > 1 else 0.0,
                        bidirectional=True,
                    )
                    self.attn = nn.Sequential(
                        nn.Linear(lstm_hidden * 2, 128),
                        nn.Tanh(),
                        nn.Linear(128, 1),
                    )
                    self.symbol_embedding = nn.Embedding(num_embeddings=num_symbols, embedding_dim=symbol_embedding_dim)
                    self.head = nn.Sequential(
                        nn.Linear(lstm_hidden * 2 + symbol_embedding_dim, 512),
                        nn.GELU(),
                        nn.Dropout(dropout),
                        nn.Linear(512, 128),
                        nn.GELU(),
                        nn.Dropout(dropout),
                        nn.Linear(128, 3),
                    )

                def forward(self, x: torch.Tensor, symbol_ids: torch.Tensor) -> torch.Tensor:
                    x = self.input_norm(x)
                    x = self.input_proj(x) + self.position[:, : x.size(1), :]
                    x = self.encoder(x)
                    x, _ = self.lstm(x)
                    weights = torch.softmax(self.attn(x), dim=1)
                    pooled = torch.sum(weights * x, dim=1)
                    symbol_vec = self.symbol_embedding(symbol_ids)
                    logits = self.head(torch.cat([pooled, symbol_vec], dim=1))
                    return logits

            def split_by_time(frame: pd.DataFrame) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame]]:
                train_frames: dict[str, pd.DataFrame] = {}
                val_frames: dict[str, pd.DataFrame] = {}
                for symbol, group in frame.groupby("symbol", sort=True):
                    split_idx = max(int(len(group) * CFG.train_split_ratio), CFG.lookback + 1)
                    train_frames[symbol] = group.iloc[:split_idx].reset_index(drop=True)
                    val_frames[symbol] = group.iloc[max(split_idx - CFG.lookback, 0) :].reset_index(drop=True)
                return train_frames, val_frames

            train_frames, val_frames = split_by_time(feature_df)
            symbols = sorted(train_frames.keys())
            symbol_to_id = {symbol: idx for idx, symbol in enumerate(symbols)}

            train_concat = pd.concat(train_frames.values(), ignore_index=True)
            feature_mean = train_concat[FEATURE_COLUMNS].mean().to_numpy(dtype=np.float32)
            feature_std = train_concat[FEATURE_COLUMNS].std().replace(0, 1.0).to_numpy(dtype=np.float32)

            def normalize_frames(frames: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
                out: dict[str, pd.DataFrame] = {}
                for symbol, frame in frames.items():
                    clone = frame.copy()
                    clone.loc[:, FEATURE_COLUMNS] = (clone[FEATURE_COLUMNS].to_numpy(dtype=np.float32) - feature_mean) / feature_std
                    out[symbol] = clone
                return out

            train_frames = normalize_frames(train_frames)
            val_frames = normalize_frames(val_frames)

            train_ds = GroupedSequenceDataset(
                frames_by_symbol=train_frames,
                feature_columns=FEATURE_COLUMNS,
                lookback=CFG.lookback,
                symbol_to_id=symbol_to_id,
            )
            val_ds = GroupedSequenceDataset(
                frames_by_symbol=val_frames,
                feature_columns=FEATURE_COLUMNS,
                lookback=CFG.lookback,
                symbol_to_id=symbol_to_id,
            )

            train_loader = DataLoader(
                train_ds,
                batch_size=CFG.batch_size,
                shuffle=True,
                num_workers=CFG.num_workers,
                pin_memory=True,
                persistent_workers=CFG.num_workers > 0,
                prefetch_factor=4 if CFG.num_workers > 0 else None,
                drop_last=False,
            )
            val_loader = DataLoader(
                val_ds,
                batch_size=CFG.eval_batch_size,
                shuffle=False,
                num_workers=CFG.num_workers,
                pin_memory=True,
                persistent_workers=CFG.num_workers > 0,
                prefetch_factor=4 if CFG.num_workers > 0 else None,
                drop_last=False,
            )

            class_counts = train_concat["label"].value_counts().sort_index()
            class_weights = torch.tensor(
                [1.0 / max(class_counts.get(i, 1), 1) for i in range(3)],
                dtype=torch.float32,
                device=DEVICE,
            )
            class_weights = class_weights / class_weights.sum() * 3.0

            base_model = CerberusSequenceClassifier(
                feature_dim=len(FEATURE_COLUMNS),
                num_symbols=len(symbols),
                lookback=CFG.lookback,
                d_model=CFG.d_model,
                nhead=CFG.nhead,
                transformer_layers=CFG.transformer_layers,
                ff_dim=CFG.ff_dim,
                lstm_hidden=CFG.lstm_hidden,
                lstm_layers=CFG.lstm_layers,
                symbol_embedding_dim=CFG.symbol_embedding_dim,
                dropout=CFG.dropout,
            ).to(DEVICE)
            model = base_model
            if torch.cuda.is_available() and hasattr(torch, "compile"):
                model = torch.compile(base_model, mode="max-autotune")

            optimizer = torch.optim.AdamW(
                base_model.parameters(),
                lr=CFG.learning_rate,
                weight_decay=CFG.weight_decay,
                fused=torch.cuda.is_available(),
            )
            scheduler = torch.optim.lr_scheduler.OneCycleLR(
                optimizer,
                max_lr=CFG.learning_rate,
                epochs=CFG.epochs,
                steps_per_epoch=max(len(train_loader), 1),
                pct_start=0.1,
            )
            scaler = torch.cuda.amp.GradScaler(enabled=False)

            def run_epoch(loader: DataLoader, train: bool) -> tuple[float, dict[str, float]]:
                model.train(mode=train)
                losses = []
                all_preds = []
                all_targets = []
                iterator = tqdm(loader, leave=False)
                for batch_x, batch_symbol, batch_y in iterator:
                    batch_x = batch_x.to(DEVICE, non_blocking=True)
                    batch_symbol = batch_symbol.to(DEVICE, non_blocking=True)
                    batch_y = batch_y.to(DEVICE, non_blocking=True)
                    with torch.set_grad_enabled(train):
                        with torch.cuda.amp.autocast(
                            enabled=CFG.amp and torch.cuda.is_available(),
                            dtype=torch.bfloat16,
                        ):
                            logits = model(batch_x, batch_symbol)
                            loss = F.cross_entropy(
                                logits,
                                batch_y,
                                weight=class_weights,
                                label_smoothing=CFG.label_smoothing,
                            )
                        if train:
                            optimizer.zero_grad(set_to_none=True)
                            scaler.scale(loss).backward()
                            scaler.unscale_(optimizer)
                            torch.nn.utils.clip_grad_norm_(model.parameters(), CFG.grad_clip_norm)
                            scaler.step(optimizer)
                            scaler.update()
                            scheduler.step()
                    probs = logits.softmax(dim=1)
                    preds = probs.argmax(dim=1)
                    losses.append(loss.item())
                    all_preds.extend(preds.detach().cpu().numpy().tolist())
                    all_targets.extend(batch_y.detach().cpu().numpy().tolist())

                metrics = {
                    "loss": float(np.mean(losses)) if losses else math.nan,
                    "accuracy": float(accuracy_score(all_targets, all_preds)) if all_targets else math.nan,
                    "macro_f1": float(f1_score(all_targets, all_preds, average="macro")) if all_targets else math.nan,
                }
                return metrics["loss"], metrics
            """
        ).strip()
    ),
    code_cell(
        dedent(
            """
            history = []
            best_state = None
            best_metric = -1.0

            for epoch in range(1, CFG.epochs + 1):
                train_loss, train_metrics = run_epoch(train_loader, train=True)
                val_loss, val_metrics = run_epoch(val_loader, train=False)
                row = {
                    "epoch": epoch,
                    "train_loss": train_metrics["loss"],
                    "train_accuracy": train_metrics["accuracy"],
                    "train_macro_f1": train_metrics["macro_f1"],
                    "val_loss": val_metrics["loss"],
                    "val_accuracy": val_metrics["accuracy"],
                    "val_macro_f1": val_metrics["macro_f1"],
                }
                history.append(row)
                print(row)
                if val_metrics["macro_f1"] >= best_metric:
                    best_metric = val_metrics["macro_f1"]
                    best_state = {
                        "model": base_model.state_dict(),
                        "optimizer": optimizer.state_dict(),
                        "config": asdict(CFG),
                        "feature_columns": FEATURE_COLUMNS,
                        "feature_mean": feature_mean.tolist(),
                        "feature_std": feature_std.tolist(),
                        "symbol_to_id": symbol_to_id,
                        "label_to_signal": LABEL_TO_SIGNAL,
                    }

            if best_state is None:
                raise RuntimeError("training did not produce a best_state")

            run_dir = Path(CFG.drive_artifact_dir) / CFG.run_name
            run_dir.mkdir(parents=True, exist_ok=True)

            model_path = run_dir / "cerberus_signal_model.pt"
            onnx_path = run_dir / "cerberus_signal_model.onnx"
            preprocessing_path = run_dir / "preprocessing.json"
            metrics_path = run_dir / "training_metrics.json"
            manifest_path = run_dir / "artifact_manifest.json"

            torch.save(best_state, model_path)
            base_model.load_state_dict(best_state["model"])
            base_model.eval()

            dummy_features = torch.randn(1, CFG.lookback, len(FEATURE_COLUMNS), device=DEVICE)
            dummy_symbol = torch.tensor([0], dtype=torch.long, device=DEVICE)

            with torch.no_grad():
                torch.onnx.export(
                    base_model,
                    (dummy_features, dummy_symbol),
                    str(onnx_path),
                    export_params=True,
                    opset_version=14,
                    do_constant_folding=True,
                    input_names=["features", "symbol_ids"],
                    output_names=["logits"],
                    dynamic_axes={
                        "features": {0: "batch_size"},
                        "symbol_ids": {0: "batch_size"},
                        "logits": {0: "batch_size"},
                    },
                )

            preprocessing_payload = {
                "feature_columns": FEATURE_COLUMNS,
                "feature_mean": feature_mean.tolist(),
                "feature_std": feature_std.tolist(),
                "symbol_to_id": symbol_to_id,
                "lookback": CFG.lookback,
            }
            preprocessing_path.write_text(json.dumps(preprocessing_payload, indent=2, ensure_ascii=False))

            metrics_payload = {
                "history": history,
                "best_macro_f1": best_metric,
                "classification_report": classification_report(
                    [],
                    [],
                    output_dict=True,
                    zero_division=0,
                ) if False else None,
            }
            metrics_path.write_text(json.dumps(metrics_payload, indent=2, ensure_ascii=False))

            manifest = {
                "task": "signal_inference",
                "model_id": CFG.model_id,
                "model_version": CFG.model_version,
                "model_source": CFG.model_source,
                "strategy_id": CFG.strategy_id,
                "engine_name": CFG.run_name,
                "signals": LABEL_TO_SIGNAL,
                "symbols": symbols,
                "feature_columns": FEATURE_COLUMNS,
                "lookback": CFG.lookback,
                "horizon": CFG.horizon,
                "threshold_bps": {
                    "up": CFG.up_threshold_bps,
                    "down": CFG.down_threshold_bps,
                },
                "training_rows": int(len(feature_df)),
                "train_samples": int(len(train_ds)),
                "val_samples": int(len(val_ds)),
                "best_macro_f1": best_metric,
                "artifact_files": {
                    "model": onnx_path.name,
                    "preprocessing": preprocessing_path.name,
                    "training_bundle": model_path.name,
                    "metrics": metrics_path.name,
                },
            }
            manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

            print("saved:", model_path)
            print("saved:", onnx_path)
            print("saved:", preprocessing_path)
            print("saved:", metrics_path)
            print("saved:", manifest_path)
            print("drive folder:", run_dir)
            """
        ).strip()
    ),
    code_cell(
        dedent(
            """
            sample_batch = next(iter(val_loader))
            base_model.load_state_dict(best_state["model"])
            base_model.eval()

            with torch.no_grad():
                batch_x, batch_symbol, batch_y = sample_batch
                logits = base_model(batch_x.to(DEVICE), batch_symbol.to(DEVICE))
                probs = logits.softmax(dim=1).cpu().numpy()
                preds = probs.argmax(axis=1)

            rows = []
            for idx in range(min(10, len(preds))):
                confidence = float(probs[idx, preds[idx]])
                rows.append(
                    {
                        "target_label": int(batch_y[idx].item()),
                        "target_signal": LABEL_TO_SIGNAL[int(batch_y[idx].item())],
                        "pred_label": int(preds[idx]),
                        "pred_signal": LABEL_TO_SIGNAL[int(preds[idx])],
                        "confidence": confidence,
                    }
                )

            pd.DataFrame(rows)
            """
        ).strip()
    ),
    md_cell(
        dedent(
            """
            ## 产物交付给我时的要求

            后续把以下二选一发给我：

            1. `artifact_manifest.json`、`cerberus_signal_model.onnx`、`preprocessing.json` 的 **可直接下载链接**
            2. 一个共享的 Google Drive 文件夹链接，且我能直接访问到上述文件

            如果链接是私有的、需要登录你自己的 Google 账号，我在这里无法直接读取；那时你需要给我公开可读链接，或者把 `artifact_manifest.json` 内容贴给我。
            """
        ).strip()
    ),
]


notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "name": "python",
            "version": "3.11",
        },
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}


output_path = Path(__file__).with_name("colab_signal_training.ipynb")
output_path.write_text(json.dumps(notebook, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"wrote {output_path}")
