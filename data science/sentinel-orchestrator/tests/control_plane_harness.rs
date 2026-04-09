use std::{
    collections::HashMap,
    future::Future,
    sync::{
        Arc,
        atomic::{AtomicUsize, Ordering},
    },
    time::Duration,
};

use async_stream::stream;
use axum::{
    Json, Router,
    body::Body,
    extract::{Path, State},
    http::{Response as HttpResponse, StatusCode, header},
    response::{IntoResponse, Response},
    routing::{get, post},
};
use bytes::Bytes;
use reqwest::Client;
use sentinel_orchestrator::{
    AppConfig, build_app, build_state,
    policy::{ApprovalStateSnapshot, OperationSnapshot},
};
use serde_json::{Value, json};
use tokio::{
    net::TcpListener,
    sync::Mutex,
    task::JoinHandle,
    time::{Instant, sleep},
};

const INTERNAL_TOKEN: &str = "test-internal-job-token";

#[derive(Clone)]
struct RunningServer {
    base_url: String,
    handle: Arc<JoinHandle<()>>,
}

impl Drop for RunningServer {
    fn drop(&mut self) {
        if Arc::strong_count(&self.handle) == 1 {
            self.handle.abort();
        }
    }
}

#[derive(Debug, Clone)]
struct ScriptedJsonResponse {
    status: StatusCode,
    body: ScriptedJsonBody,
    delay_ms: u64,
}

impl ScriptedJsonResponse {
    fn json(status: StatusCode, body: Value) -> Self {
        Self {
            status,
            body: ScriptedJsonBody::Json(body),
            delay_ms: 0,
        }
    }

    fn raw(status: StatusCode, body: impl Into<String>) -> Self {
        Self {
            status,
            body: ScriptedJsonBody::Raw(body.into()),
            delay_ms: 0,
        }
    }

    fn delayed(mut self, delay_ms: u64) -> Self {
        self.delay_ms = delay_ms;
        self
    }
}

#[derive(Debug, Clone)]
enum ScriptedJsonBody {
    Json(Value),
    Raw(String),
}

#[derive(Debug, Clone)]
struct ScriptedSseResponse {
    status: StatusCode,
    chunks: Vec<(u64, String)>,
}

impl ScriptedSseResponse {
    fn from_text(status: StatusCode, body: impl Into<String>) -> Self {
        Self {
            status,
            chunks: vec![(0, body.into())],
        }
    }
}

#[derive(Clone)]
struct MockWorkerState {
    operations: Arc<Mutex<HashMap<String, OperationSnapshot>>>,
    get_operation_response: Arc<Mutex<Option<ScriptedJsonResponse>>>,
    dispatch_response: Arc<Mutex<ScriptedJsonResponse>>,
    retry_response: Arc<Mutex<ScriptedJsonResponse>>,
    approve_response: Arc<Mutex<ScriptedJsonResponse>>,
    cancel_response: Arc<Mutex<ScriptedJsonResponse>>,
    control_tasks_response: Arc<Mutex<Value>>,
    stream_response: Arc<Mutex<ScriptedSseResponse>>,
    dispatch_calls: Arc<AtomicUsize>,
    get_operation_calls: Arc<AtomicUsize>,
}

impl Default for MockWorkerState {
    fn default() -> Self {
        Self {
            operations: Arc::new(Mutex::new(HashMap::new())),
            get_operation_response: Arc::new(Mutex::new(None)),
            dispatch_response: Arc::new(Mutex::new(ScriptedJsonResponse::json(
                StatusCode::OK,
                json!({"success": true, "data": {"accepted": true}}),
            ))),
            retry_response: Arc::new(Mutex::new(ScriptedJsonResponse::json(
                StatusCode::OK,
                json!({"data": default_operation("op-1", "queued", "analysis", "python_worker")}),
            ))),
            approve_response: Arc::new(Mutex::new(ScriptedJsonResponse::json(
                StatusCode::OK,
                json!({"data": default_operation("op-1", "queued", "analysis", "python_worker")}),
            ))),
            cancel_response: Arc::new(Mutex::new(ScriptedJsonResponse::json(
                StatusCode::OK,
                json!({"data": default_operation("op-1", "cancelled", "analysis", "python_worker")}),
            ))),
            control_tasks_response: Arc::new(Mutex::new(json!({
                "success": true,
                "data": { "control_tasks": [] }
            }))),
            stream_response: Arc::new(Mutex::new(ScriptedSseResponse::from_text(
                StatusCode::OK,
                "event: operation.snapshot\ndata: {\"status\":\"running\"}\n\n",
            ))),
            dispatch_calls: Arc::new(AtomicUsize::new(0)),
            get_operation_calls: Arc::new(AtomicUsize::new(0)),
        }
    }
}

impl MockWorkerState {
    async fn insert_operation(&self, operation: OperationSnapshot) {
        self.operations
            .lock()
            .await
            .insert(operation.operation_id(), operation);
    }

    async fn set_get_operation_response(&self, response: Option<ScriptedJsonResponse>) {
        *self.get_operation_response.lock().await = response;
    }

    async fn set_dispatch_response(&self, response: ScriptedJsonResponse) {
        *self.dispatch_response.lock().await = response;
    }

    async fn set_retry_response(&self, response: ScriptedJsonResponse) {
        *self.retry_response.lock().await = response;
    }

    async fn set_approve_response(&self, response: ScriptedJsonResponse) {
        *self.approve_response.lock().await = response;
    }

    async fn set_cancel_response(&self, response: ScriptedJsonResponse) {
        *self.cancel_response.lock().await = response;
    }

    async fn set_control_tasks_response(&self, response: Value) {
        *self.control_tasks_response.lock().await = response;
    }

    async fn set_stream_response(&self, response: ScriptedSseResponse) {
        *self.stream_response.lock().await = response;
    }
}

#[derive(Clone)]
struct MockWorkerAppState {
    worker: MockWorkerState,
}

#[tokio::test]
async fn duplicate_dispatch_is_deduplicated_and_only_one_worker_dispatch_occurs() {
    let worker = MockWorkerState::default();
    worker
        .insert_operation(default_operation_snapshot(
            "op-dup",
            "queued",
            "analysis",
            "python_worker",
        ))
        .await;
    worker
        .set_get_operation_response(Some(
            ScriptedJsonResponse::json(
                StatusCode::OK,
                json!({"data": default_operation("op-dup", "queued", "analysis", "python_worker")}),
            )
            .delayed(200),
        ))
        .await;

    let worker_server = spawn_mock_worker(worker.clone()).await;
    let orchestrator = spawn_orchestrator(worker_server.base_url.clone(), 2).await;

    let first = post_json(
        &orchestrator,
        "/internal/operations/op-dup/dispatch",
        json!({}),
    )
    .await;
    let second = post_json(
        &orchestrator,
        "/internal/operations/op-dup/dispatch",
        json!({}),
    )
    .await;

    assert_eq!(first.0, StatusCode::ACCEPTED);
    assert_eq!(first.1["decision"], "accepted");
    assert_eq!(second.0, StatusCode::ACCEPTED);
    assert_eq!(second.1["decision"], "already_managed");

    wait_for(
        Duration::from_secs(2),
        || async { worker.dispatch_calls.load(Ordering::Relaxed) == 1 },
        "worker dispatch count to reach 1",
    )
    .await;
}

#[tokio::test]
async fn approve_requeues_dispatch_once_when_operation_returns_to_queue() {
    let worker = MockWorkerState::default();
    worker
        .insert_operation(default_operation_snapshot(
            "op-approve",
            "queued",
            "analysis",
            "python_worker",
        ))
        .await;
    worker
        .set_approve_response(ScriptedJsonResponse::json(
            StatusCode::OK,
            json!({"data": default_operation("op-approve", "queued", "analysis", "python_worker")}),
        ))
        .await;

    let worker_server = spawn_mock_worker(worker.clone()).await;
    let orchestrator = spawn_orchestrator(worker_server.base_url.clone(), 2).await;

    let response = post_json(
        &orchestrator,
        "/internal/operations/op-approve/approve",
        json!({"approved": true, "message": "ship it"}),
    )
    .await;

    assert_eq!(response.0, StatusCode::OK);
    assert_eq!(response.1["decision"], "enqueue_dispatch");
    assert_eq!(response.1["queued"], true);

    wait_for(
        Duration::from_secs(2),
        || async { worker.dispatch_calls.load(Ordering::Relaxed) == 1 },
        "worker dispatch count after approval",
    )
    .await;
}

#[tokio::test]
async fn retry_and_cancel_concurrency_does_not_leave_a_stale_active_lease() {
    let worker = MockWorkerState::default();
    worker
        .insert_operation(default_operation_snapshot(
            "op-race",
            "failed",
            "analysis",
            "python_worker",
        ))
        .await;
    worker
        .set_retry_response(ScriptedJsonResponse::json(
            StatusCode::OK,
            json!({"data": default_operation("op-race", "queued", "analysis", "python_worker")}),
        ))
        .await;
    worker
        .set_cancel_response(ScriptedJsonResponse::json(
            StatusCode::OK,
            json!({"data": default_operation("op-race", "cancelled", "analysis", "python_worker")}),
        ))
        .await;
    worker
        .set_get_operation_response(Some(
            ScriptedJsonResponse::json(
                StatusCode::OK,
                json!({"data": default_operation("op-race", "cancelled", "analysis", "python_worker")}),
            )
            .delayed(150),
        ))
        .await;

    let worker_server = spawn_mock_worker(worker.clone()).await;
    let orchestrator = spawn_orchestrator(worker_server.base_url.clone(), 2).await;

    let (retry_response, cancel_response) = tokio::join!(
        post_json(
            &orchestrator,
            "/internal/operations/op-race/retry",
            json!({})
        ),
        post_json(
            &orchestrator,
            "/internal/operations/op-race/cancel",
            json!({})
        )
    );

    assert_eq!(retry_response.0, StatusCode::OK);
    assert_eq!(retry_response.1["decision"], "enqueue_dispatch");
    assert_eq!(cancel_response.0, StatusCode::OK);
    assert_eq!(cancel_response.1["decision"], "cancelled");

    wait_for(
        Duration::from_secs(2),
        || {
            let orchestrator = orchestrator.clone();
            async move {
                let status = get_json(&orchestrator, "/statusz").await;
                status.1["active_operations"] == 0
            }
        },
        "active leases to drain after retry/cancel race",
    )
    .await;
    assert_eq!(worker.dispatch_calls.load(Ordering::Relaxed), 0);
}

#[tokio::test]
async fn bad_status_decode_error_and_read_timeout_are_reflected_in_statusz() {
    let worker = MockWorkerState::default();
    worker
        .insert_operation(default_operation_snapshot(
            "op-health",
            "queued",
            "analysis",
            "python_worker",
        ))
        .await;

    let worker_server = spawn_mock_worker(worker.clone()).await;
    let orchestrator = spawn_orchestrator(worker_server.base_url.clone(), 1).await;

    worker
        .set_get_operation_response(Some(ScriptedJsonResponse::raw(StatusCode::OK, "{not-json")))
        .await;
    let _ = post_json(
        &orchestrator,
        "/internal/operations/op-health/dispatch",
        json!({}),
    )
    .await;
    wait_for(
        Duration::from_secs(2),
        || async { worker.get_operation_calls.load(Ordering::Relaxed) >= 1 },
        "decode-error fetch operation call",
    )
    .await;
    wait_for(
        Duration::from_secs(2),
        || {
            let orchestrator = orchestrator.clone();
            async move {
                let status = get_json(&orchestrator, "/statusz").await;
                status.1["last_upstream_error"]["kind"] == "decode_error"
            }
        },
        "decode error to surface in statusz",
    )
    .await;

    worker
        .set_get_operation_response(Some(ScriptedJsonResponse::json(
            StatusCode::OK,
            json!({"data": default_operation("op-health", "queued", "analysis", "python_worker")}),
        )))
        .await;
    worker
        .set_dispatch_response(ScriptedJsonResponse::json(
            StatusCode::BAD_GATEWAY,
            json!({"success": false, "error": {"code": "BROKEN_UPSTREAM"}}),
        ))
        .await;
    let _ = post_json(
        &orchestrator,
        "/internal/operations/op-health/dispatch",
        json!({}),
    )
    .await;
    wait_for(
        Duration::from_secs(2),
        || async { worker.dispatch_calls.load(Ordering::Relaxed) >= 1 },
        "bad-status worker dispatch call",
    )
    .await;
    wait_for(
        Duration::from_secs(2),
        || {
            let orchestrator = orchestrator.clone();
            async move {
                let status = get_json(&orchestrator, "/statusz").await;
                status.1["last_upstream_error"]["kind"] == "bad_status"
            }
        },
        "bad status to surface in statusz",
    )
    .await;

    worker
        .set_dispatch_response(
            ScriptedJsonResponse::json(
                StatusCode::OK,
                json!({"success": true, "data": {"accepted": true}}),
            )
            .delayed(1500),
        )
        .await;
    let _ = post_json(
        &orchestrator,
        "/internal/operations/op-health/dispatch",
        json!({}),
    )
    .await;
    wait_for(
        Duration::from_secs(3),
        || async { worker.dispatch_calls.load(Ordering::Relaxed) >= 2 },
        "read-timeout worker dispatch call",
    )
    .await;
    wait_for(
        Duration::from_secs(3),
        || {
            let orchestrator = orchestrator.clone();
            async move {
                let status = get_json(&orchestrator, "/statusz").await;
                status.1["last_upstream_error"]["kind"] == "read_timeout"
            }
        },
        "read timeout to surface in statusz",
    )
    .await;
    let final_status = get_json(&orchestrator, "/statusz").await;
    assert_eq!(
        final_status.1["connectors"][0]["connector_name"],
        "python_worker"
    );
    assert_eq!(final_status.1["connectors"][0]["state"], "failed");
    assert!(
        final_status.1["degraded_mode"]["unavailable_capabilities"]
            .as_array()
            .is_some_and(|capabilities| capabilities
                .iter()
                .any(|value| value == "operations.dispatch"))
    );
}

#[tokio::test]
async fn stream_endpoint_normalizes_upstream_eof_to_closed_frame() {
    let worker = MockWorkerState::default();
    worker
        .set_stream_response(ScriptedSseResponse::from_text(
            StatusCode::OK,
            concat!(
                "event: operation.snapshot\n",
                "id: snap-1\n",
                "data: {\"status\":\"running\",\"step\":1}\n\n",
                ": keepalive\n\n"
            ),
        ))
        .await;

    let worker_server = spawn_mock_worker(worker.clone()).await;
    let orchestrator = spawn_orchestrator(worker_server.base_url.clone(), 2).await;

    let response = Client::new()
        .get(format!(
            "{}/internal/operations/op-stream/stream",
            orchestrator.base_url
        ))
        .header("X-Internal-Job-Token", INTERNAL_TOKEN)
        .send()
        .await
        .expect("stream request should succeed");
    assert_eq!(response.status(), StatusCode::OK);
    let body = response.text().await.expect("stream body");

    assert!(body.contains("event: snapshot"));
    assert!(body.contains("\"frame_type\":\"snapshot\""));
    assert!(body.contains("event: heartbeat"));
    assert!(body.contains("event: closed"));
    assert!(body.contains("\"reason\":\"upstream_eof\""));
}

#[tokio::test]
async fn runtime_snapshot_can_be_rebuilt_after_orchestrator_restart() {
    let worker = MockWorkerState::default();
    worker
        .set_control_tasks_response(json!({
            "success": true,
            "data": {
                "control_tasks": [{
                    "id": "fetch_data_hourly",
                    "title": "Fetch data hourly",
                    "enabled": true,
                    "next_run_at": null,
                    "dependencies": [],
                    "latest_operation": {
                        "id": "op-runtime",
                        "status": "queued",
                        "type": "analysis",
                        "execution_target": "python_worker",
                    }
                }]
            }
        }))
        .await;

    let worker_server = spawn_mock_worker(worker.clone()).await;
    let first = spawn_orchestrator(worker_server.base_url.clone(), 2).await;
    let first_snapshot = get_json(&first, "/internal/runtime/snapshot?uid=system").await;
    assert_eq!(first_snapshot.0, StatusCode::OK);
    assert_eq!(first_snapshot.1["control_tasks"]["count"], 1);

    drop(first);

    let second = spawn_orchestrator(worker_server.base_url.clone(), 2).await;
    let second_snapshot = get_json(&second, "/internal/runtime/snapshot?uid=system&fresh=1").await;
    assert_eq!(second_snapshot.0, StatusCode::OK);
    assert_eq!(second_snapshot.1["control_tasks"]["count"], 1);
    assert_eq!(
        second_snapshot.1["control_plane"]["managed_by"],
        "sentinel_orchestrator"
    );
}

async fn spawn_orchestrator(worker_base_url: String, dispatch_timeout_secs: u64) -> RunningServer {
    let config = Arc::new(AppConfig {
        host: "127.0.0.1".to_string(),
        port: 0,
        python_worker_base_url: Some(worker_base_url),
        heavy_worker_base_url: None,
        internal_job_token: INTERNAL_TOKEN.to_string(),
        max_light_parallel: 2,
        max_heavy_parallel: 1,
        dispatch_timeout_secs,
        runtime_snapshot_ttl_secs: 1,
    });
    let state = build_state(config).expect("app state");
    let app = build_app(state);
    spawn_router(app).await
}

async fn spawn_mock_worker(worker: MockWorkerState) -> RunningServer {
    let app = Router::new()
        .route(
            "/internal/operations/{operation_id}",
            get(mock_get_operation),
        )
        .route(
            "/internal/operations/{operation_id}/dispatch",
            post(mock_dispatch_operation),
        )
        .route(
            "/internal/operations/{operation_id}/retry",
            post(mock_retry_operation),
        )
        .route(
            "/internal/operations/{operation_id}/approve",
            post(mock_approve_operation),
        )
        .route(
            "/internal/operations/{operation_id}/cancel",
            post(mock_cancel_operation),
        )
        .route(
            "/internal/operations/{operation_id}/stream",
            get(mock_stream_operation),
        )
        .route("/internal/control-tasks", get(mock_list_control_tasks))
        .route("/internal/runtime/compute-status", get(mock_compute_status))
        .route("/internal/compute/rollout", get(mock_compute_rollout))
        .with_state(MockWorkerAppState { worker });
    spawn_router(app).await
}

async fn spawn_router(app: Router) -> RunningServer {
    let listener = TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind test listener");
    let address = listener.local_addr().expect("listener address");
    let handle = tokio::spawn(async move {
        axum::serve(listener, app)
            .await
            .expect("test server should run");
    });
    RunningServer {
        base_url: format!("http://{}", address),
        handle: Arc::new(handle),
    }
}

async fn post_json(server: &RunningServer, path: &str, payload: Value) -> (StatusCode, Value) {
    let response = Client::new()
        .post(format!("{}{}", server.base_url, path))
        .header("X-Internal-Job-Token", INTERNAL_TOKEN)
        .json(&payload)
        .send()
        .await
        .expect("request should succeed");
    let status = response.status();
    let body = response.json::<Value>().await.expect("json body");
    (status, body)
}

async fn get_json(server: &RunningServer, path: &str) -> (StatusCode, Value) {
    let mut request = Client::new().get(format!("{}{}", server.base_url, path));
    if path.starts_with("/internal/") {
        request = request.header("X-Internal-Job-Token", INTERNAL_TOKEN);
    }
    let response = request.send().await.expect("request should succeed");
    let status = response.status();
    let body = response.json::<Value>().await.expect("json body");
    (status, body)
}

async fn wait_for<F, Fut>(timeout: Duration, mut predicate: F, label: &str)
where
    F: FnMut() -> Fut,
    Fut: Future<Output = bool>,
{
    let deadline = Instant::now() + timeout;
    loop {
        if predicate().await {
            return;
        }
        assert!(Instant::now() < deadline, "timed out waiting for {label}");
        sleep(Duration::from_millis(25)).await;
    }
}

async fn mock_get_operation(
    State(state): State<MockWorkerAppState>,
    Path(operation_id): Path<String>,
) -> Response {
    state
        .worker
        .get_operation_calls
        .fetch_add(1, Ordering::Relaxed);
    if let Some(response) = state.worker.get_operation_response.lock().await.clone() {
        return scripted_json_response(response).await;
    }

    let operations = state.worker.operations.lock().await;
    let operation = operations.get(&operation_id).cloned().unwrap_or_else(|| {
        default_operation_snapshot(&operation_id, "queued", "analysis", "python_worker")
    });
    scripted_json_response(ScriptedJsonResponse::json(
        StatusCode::OK,
        json!({"data": operation}),
    ))
    .await
}

async fn mock_dispatch_operation(State(state): State<MockWorkerAppState>) -> Response {
    state.worker.dispatch_calls.fetch_add(1, Ordering::Relaxed);
    let response = state.worker.dispatch_response.lock().await.clone();
    scripted_json_response(response).await
}

async fn mock_retry_operation(
    State(state): State<MockWorkerAppState>,
    Path(operation_id): Path<String>,
) -> Response {
    let response = state.worker.retry_response.lock().await.clone();
    maybe_store_operation(&state.worker, &operation_id, &response).await;
    scripted_json_response(response).await
}

async fn mock_approve_operation(
    State(state): State<MockWorkerAppState>,
    Path(operation_id): Path<String>,
) -> Response {
    let response = state.worker.approve_response.lock().await.clone();
    maybe_store_operation(&state.worker, &operation_id, &response).await;
    scripted_json_response(response).await
}

async fn mock_cancel_operation(
    State(state): State<MockWorkerAppState>,
    Path(operation_id): Path<String>,
) -> Response {
    let response = state.worker.cancel_response.lock().await.clone();
    maybe_store_operation(&state.worker, &operation_id, &response).await;
    scripted_json_response(response).await
}

async fn mock_stream_operation(State(state): State<MockWorkerAppState>) -> Response {
    let response = state.worker.stream_response.lock().await.clone();
    let status = response.status;
    let body_stream = stream! {
        for (delay_ms, chunk) in response.chunks {
            if delay_ms > 0 {
                sleep(Duration::from_millis(delay_ms)).await;
            }
            yield Ok::<Bytes, std::io::Error>(Bytes::from(chunk));
        }
    };
    HttpResponse::builder()
        .status(status)
        .header(header::CONTENT_TYPE, "text/event-stream")
        .body(Body::from_stream(body_stream))
        .expect("sse response")
        .into_response()
}

async fn mock_list_control_tasks(State(state): State<MockWorkerAppState>) -> Response {
    let body = state.worker.control_tasks_response.lock().await.clone();
    scripted_json_response(ScriptedJsonResponse::json(StatusCode::OK, body)).await
}

async fn mock_compute_status() -> Response {
    scripted_json_response(ScriptedJsonResponse::json(
        StatusCode::OK,
        json!({
            "data": {
                "status": "ok",
                "message": "mock",
                "active_backend": "python_pandas",
                "preferred_backend": "python_pandas",
                "native_enabled": false,
                "native_available": false,
                "profiled_components": 0,
                "benchmark_ready": false,
                "hottest_component": "--",
                "last_updated_at": "",
                "rollout": {
                    "enabled": false,
                    "updated_at": "",
                    "updated_by": "",
                    "components": []
                }
            }
        }),
    ))
    .await
}

async fn mock_compute_rollout() -> Response {
    scripted_json_response(ScriptedJsonResponse::json(
        StatusCode::OK,
        json!({
            "data": {
                "enabled": false,
                "updated_at": "",
                "updated_by": "",
                "components": []
            }
        }),
    ))
    .await
}

async fn maybe_store_operation(
    worker: &MockWorkerState,
    fallback_operation_id: &str,
    response: &ScriptedJsonResponse,
) {
    let ScriptedJsonBody::Json(body) = &response.body else {
        return;
    };

    let operation_value = body
        .get("data")
        .cloned()
        .unwrap_or_else(|| json!({ "id": fallback_operation_id }));
    if let Ok(operation) = serde_json::from_value::<OperationSnapshot>(operation_value) {
        worker
            .operations
            .lock()
            .await
            .insert(operation.operation_id(), operation);
    }
}

async fn scripted_json_response(response: ScriptedJsonResponse) -> Response {
    if response.delay_ms > 0 {
        sleep(Duration::from_millis(response.delay_ms)).await;
    }

    match response.body {
        ScriptedJsonBody::Json(body) => (response.status, Json(body)).into_response(),
        ScriptedJsonBody::Raw(body) => HttpResponse::builder()
            .status(response.status)
            .header(header::CONTENT_TYPE, "application/json")
            .body(Body::from(body))
            .expect("raw response")
            .into_response(),
    }
}

fn default_operation_snapshot(
    operation_id: &str,
    status: &str,
    operation_type: &str,
    execution_target: &str,
) -> OperationSnapshot {
    OperationSnapshot {
        id: operation_id.to_string(),
        job_id: operation_id.to_string(),
        r#type: operation_type.to_string(),
        status: status.to_string(),
        execution_target: execution_target.to_string(),
        control_task_id: None,
        approval_state: ApprovalStateSnapshot::default(),
    }
}

fn default_operation(
    operation_id: &str,
    status: &str,
    operation_type: &str,
    execution_target: &str,
) -> Value {
    serde_json::to_value(default_operation_snapshot(
        operation_id,
        status,
        operation_type,
        execution_target,
    ))
    .expect("operation json")
}
