# Sentinel Orchestrator

Rust control-plane sidecar for the industrial operations runtime.

## Responsibility

- Own internal control-plane entrypoints such as `/internal/operations/{id}/dispatch`
- Sit between Cloud Tasks and the Python worker plane
- Evolve into the place where timeout, cancellation, retry, approval and event-stream policies live

It does **not** replace the Python analysis core. Python still owns analysis,
training, optimization and RAG execution.

## Environment Variables

- `HOST`: bind host, defaults to `0.0.0.0`
- `PORT`: bind port, defaults to `8080`
- `PYTHON_WORKER_BASE_URL`: base URL of the Python worker plane
- `INTERNAL_JOB_TOKEN`: shared internal token forwarded to Python internal APIs
- `MAX_LIGHT_PARALLEL`: max in-flight light operations, defaults to `4`
- `MAX_HEAVY_PARALLEL`: max in-flight heavy operations, defaults to `2`
- `DISPATCH_TIMEOUT_SECS`: upstream execution timeout for a dispatched operation, defaults to `1800`

## What The Orchestrator Now Owns

- Dispatch de-duplication at the orchestrator entrypoint
- Light/heavy lane concurrency limits
- Background dispatch fan-out so callers get `202 Accepted` immediately
- Internal stream, retry, cancel, approve and control-task proxy surfaces

Python still owns execution semantics and persistence, but dispatch authority now
prefers the Rust control plane whenever `ORCHESTRATOR_BASE_URL` is configured.

## Local Run

```bash
cd "/Users/achilles/Documents/code/data science/sentinel-orchestrator"
cargo run
```

## Build Check

```bash
cd "/Users/achilles/Documents/code/data science/sentinel-orchestrator"
cargo check
```

## Deploy

Use the dedicated deployment script from the project root:

```bash
cd "/Users/achilles/Documents/code/data science"
chmod +x scripts/deploy_orchestrator.sh
./scripts/deploy_orchestrator.sh
```
