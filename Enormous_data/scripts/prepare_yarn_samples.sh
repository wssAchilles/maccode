#!/usr/bin/env sh
set -eu

RAW_INPUT="${RAW_INPUT:-data/raw/kaggle/ecommerce_behavior/*.csv}"
PERCENTS="${PERCENTS:-1 5}"

for percent in $PERCENTS; do
  label="${percent}pct"
  output="data/sample/ecommerce_user_sample_${label}.csv"
  input_dir="/user/course/ecommerce_behavior_user_sample_${label}"

  python scripts/create_user_sample.py \
    --input "$RAW_INPUT" \
    --output "$output" \
    --percent "$percent"

  docker compose --profile yarn-lab exec -T \
    -e YARN_INPUT_DIR="$input_dir" \
    spark-client \
    /app/scripts/init_yarn_lab.sh "/app/$output"
done
