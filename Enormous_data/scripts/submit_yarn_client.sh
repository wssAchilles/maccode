#!/usr/bin/env sh
set -eu

CONFIG_PATH="${1:-configs/yarn-client.yaml}"
RUN_ID="${2:-}"
PROJECT_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PYFILES_PATH="$PROJECT_ROOT/build/spark_jobs.zip"
DRIVER_HOST="${SPARK_DRIVER_HOST:-$(hostname -f 2>/dev/null || hostname)}"
PYTHON_BIN="${PYTHON_BIN:-$PROJECT_ROOT/.venv/bin/python}"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Python virtual environment not found at $PYTHON_BIN. Create .venv or set PYTHON_BIN." >&2
  exit 1
fi

mkdir -p "$PROJECT_ROOT/build"
cd "$PROJECT_ROOT"

"$PYTHON_BIN" - <<'PY'
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

target = Path("build/spark_jobs.zip")
with ZipFile(target, "w", ZIP_DEFLATED) as archive:
    for path in Path("spark_jobs").rglob("*.py"):
        archive.write(path, path.as_posix())
PY

spark-class org.apache.hadoop.fs.FsShell -mkdir -p /spark-history /user/course/ecommerce_behavior_processed || true

SPARK_SUBMIT_CONF_ARGS="$(CONFIG_PATH="$CONFIG_PATH" "$PYTHON_BIN" - <<'PY'
import os

import yaml


def format_value(value):
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


with open(os.environ["CONFIG_PATH"], "r", encoding="utf-8") as handle:
    config = yaml.safe_load(handle) or {}

spark_configs = (config.get("spark") or {}).get("configs") or {}
driver_memory = spark_configs.get("spark.driver.memory")
if driver_memory:
    print(f"--driver-memory {format_value(driver_memory)}")

for key, value in spark_configs.items():
    if value is None or key == "spark.driver.memory":
        continue
    print(f"--conf {key}={format_value(value)}")
PY
)"

if [ -n "$RUN_ID" ]; then
  # shellcheck disable=SC2086
  exec spark-submit \
    --master yarn \
    --deploy-mode client \
    $SPARK_SUBMIT_CONF_ARGS \
    --conf spark.driver.bindAddress=0.0.0.0 \
    --conf spark.driver.host="$DRIVER_HOST" \
    --py-files "$PYFILES_PATH" \
    "$PROJECT_ROOT/spark_jobs/main.py" \
    --config "$CONFIG_PATH" \
    --run-id "$RUN_ID"
fi

# shellcheck disable=SC2086
exec spark-submit \
  --master yarn \
  --deploy-mode client \
  $SPARK_SUBMIT_CONF_ARGS \
  --conf spark.driver.bindAddress=0.0.0.0 \
  --conf spark.driver.host="$DRIVER_HOST" \
  --py-files "$PYFILES_PATH" \
  "$PROJECT_ROOT/spark_jobs/main.py" \
  --config "$CONFIG_PATH"
