# Cerberus Colab Artifact Spec

训练产物请至少包含以下文件：

- `cerberus_signal_model.pt`
- `cerberus_signal_model.onnx`
- `preprocessing.json`
- `artifact_manifest.json`
- `training_metrics.json`

`artifact_manifest.json` 至少应包含：

- `task`: 固定为 `signal_inference`
- `model_id`
- `model_version`
- `model_source`
- `strategy_id`
- `engine_name`
- `signals`
- `symbols`
- `feature_columns`
- `lookback`
- `horizon`

当前线上推理契约需要最终映射为：

- `strategy_id`
- `signal`，值必须是 `BUY` / `SELL` / `HOLD`
- `confidence`，范围必须是 `0..1`
- `engine`
- `model_id`
- `model_version`
- `metadata`

`preprocessing.json` 至少应包含：

- `feature_columns`
- `feature_mean`
- `feature_std`
- `symbol_to_id`
- `lookback`

后续把 Google Drive 链接给我时，请保证满足以下任一条件：

- 文件是公开可读的直接下载链接
- Drive 文件夹已共享并且链接可直接访问

如果是仅你个人账号可见的私有链接，我这里无法直接读取。
