#!/usr/bin/env sh
set -eu

INPUT_DIR="${YARN_INPUT_DIR:-/user/course/ecommerce_behavior_user_sample_1pct}"
PROCESSED_DIR="${YARN_PROCESSED_DIR:-/user/course/ecommerce_behavior_processed}"
LOCAL_INPUT_PATH="${1:-}"

spark-class org.apache.hadoop.fs.FsShell -mkdir -p /spark-history "$PROCESSED_DIR"

if [ -n "$LOCAL_INPUT_PATH" ]; then
  spark-class org.apache.hadoop.fs.FsShell -rm -r -f "$INPUT_DIR" || true
  spark-class org.apache.hadoop.fs.FsShell -mkdir -p "$INPUT_DIR"
  spark-class org.apache.hadoop.fs.FsShell -put -f "$LOCAL_INPUT_PATH" "$INPUT_DIR/"
else
  spark-class org.apache.hadoop.fs.FsShell -mkdir -p "$INPUT_DIR"
fi

spark-class org.apache.hadoop.fs.FsShell -ls /spark-history "$INPUT_DIR" "$PROCESSED_DIR"
