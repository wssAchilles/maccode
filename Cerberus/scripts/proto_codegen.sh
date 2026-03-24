#!/usr/bin/env bash
set -euo pipefail

if command -v buf >/dev/null 2>&1; then
  (cd proto && buf lint && buf generate)
else
  docker run --rm -v "$(pwd):/workspace" -w /workspace/proto bufbuild/buf lint
  docker run --rm -v "$(pwd):/workspace" -w /workspace/proto bufbuild/buf generate
fi

# Ensure Python generated packages are importable when installed as a package.
for file in \
  services/strategy-py/app/gen/__init__.py \
  services/strategy-py/app/gen/cerberus/__init__.py \
  services/strategy-py/app/gen/cerberus/order/__init__.py \
  services/strategy-py/app/gen/cerberus/order/v1/__init__.py \
  services/strategy-py/app/gen/cerberus/market/__init__.py \
  services/strategy-py/app/gen/cerberus/market/v1/__init__.py \
  services/strategy-py/app/gen/cerberus/strategy/__init__.py \
  services/strategy-py/app/gen/cerberus/strategy/v1/__init__.py
do
  mkdir -p "$(dirname "$file")"
  touch "$file"
done
