#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
NATIVE_DIR="${ROOT_DIR}/back/native/rolling_features"

if [ ! -d "${NATIVE_DIR}" ]; then
  echo "❌ Native compute directory not found: ${NATIVE_DIR}"
  exit 1
fi

if [ -x "${ROOT_DIR}/venv/bin/python" ]; then
  PYTHON_BIN="${ROOT_DIR}/venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
else
  echo "❌ python3 is required to build the native module"
  exit 1
fi

echo "🚀 Building optional native compute backend with ${PYTHON_BIN}"
"${PYTHON_BIN}" -m pip install --quiet pybind11 setuptools wheel
cd "${NATIVE_DIR}"
"${PYTHON_BIN}" setup.py build_ext --inplace
echo "✅ Native compute backend built in ${NATIVE_DIR}"

