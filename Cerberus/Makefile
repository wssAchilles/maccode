SHELL := /bin/zsh

.PHONY: help setup strategy-sync frontend-install compose-up compose-down proto-lint proto-generate test rust-check cpp-test smoke secrets-sync-exchange gateway-deploy-source gateway-deploy-cached strategy-deploy-source

help:
	@echo "Targets:"
	@echo "  setup            - install frontend deps + sync python deps"
	@echo "  strategy-sync    - sync strategy Python dependencies into .venv via uv"
	@echo "  frontend-install - install frontend npm dependencies"
	@echo "  compose-up       - run local microservices stack"
	@echo "  compose-down     - stop local microservices stack"
	@echo "  proto-lint       - run Buf lint + breaking (requires buf)"
	@echo "  proto-generate   - run Buf code generation (requires buf)"
	@echo "  test             - run Python and C++ tests"
	@echo "  rust-check       - run cargo check on gateway"
	@echo "  cpp-test         - run C++ matching tests"
	@echo "  smoke            - run local contract smoke (health/ready/request-id/error-envelope/metrics)"
	@echo "  secrets-sync-exchange - sync BINANCE/ALPACA env secrets to GCP Secret Manager"
	@echo "  gateway-deploy-source - deploy gateway to Cloud Run from source with secret refs"
	@echo "  gateway-deploy-cached - deploy gateway via cached Docker image (faster repeat deploys)"
	@echo "  strategy-deploy-source - deploy strategy to Cloud Run from source with secret refs"

setup: frontend-install strategy-sync

frontend-install:
	cd apps/frontend && npm install

strategy-sync:
	source .venv/bin/activate && \
	uv lock --project services/strategy-py && \
	uv sync --project services/strategy-py --python .venv/bin/python --active --frozen --all-groups

compose-up:
	docker compose up -d --build

compose-down:
	docker compose down

proto-lint:
	if command -v buf >/dev/null 2>&1; then \
		cd proto && buf lint; \
	else \
		docker run --rm -v "$$(pwd):/workspace" -w /workspace/proto bufbuild/buf lint; \
	fi

proto-generate:
	./scripts/proto_codegen.sh

test:
	source .venv/bin/activate && uv run --project services/strategy-py --active pytest services/strategy-py/tests

rust-check:
	cd services/gateway-rs && cargo check

cpp-test:
	cd services/matching-cpp && cmake -S . -B build && cmake --build build && ctest --test-dir build --output-on-failure

smoke:
	./scripts/smoke_local.sh

secrets-sync-exchange:
	./scripts/sync_gcp_exchange_secrets.sh cerberus-9d94f asia-east2

gateway-deploy-source:
	./scripts/deploy_gateway_source.sh cerberus-9d94f asia-east2

gateway-deploy-cached:
	./scripts/deploy_gateway_cached.sh cerberus-9d94f asia-east2

strategy-deploy-source:
	./scripts/deploy_strategy_source.sh cerberus-9d94f asia-east2
