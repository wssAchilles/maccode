environment = "staging"

firebase_enabled       = true
supabase_enabled       = true
matching_enabled       = true
firebase_auth_required = true
jwt_auth_enabled       = true

internal_services_ingress                 = true
strategy_public_access                    = false
matching_public_access                    = false
gateway_public_access                     = true
matching_max_inflight_requests            = 1024
matching_inflight_acquire_timeout_ms      = 30
matching_backpressure_retry_sleep_ms      = 1
strategy_event_stream_maxlen              = 20000
redis_order_events_legacy_pubsub_fallback = true
strategy_summary_cache_ttl_ms             = 1500
strategy_summary_batch_window_ms          = 100

strategy_internal_auth_enabled              = true
strategy_upstream_circuit_enabled           = true
strategy_upstream_circuit_failure_threshold = 6

cloud_run_gateway = {
  min_instance_count               = 1
  max_instance_count               = 40
  max_instance_request_concurrency = 80
  timeout_seconds                  = 900
  cpu                              = "2"
  memory                           = "2Gi"
  cpu_idle                         = false
  startup_cpu_boost                = true
}

cloud_run_strategy = {
  min_instance_count               = 1
  max_instance_count               = 30
  max_instance_request_concurrency = 30
  timeout_seconds                  = 300
  cpu                              = "2"
  memory                           = "3Gi"
  cpu_idle                         = false
  startup_cpu_boost                = true
}

cloud_run_matching = {
  min_instance_count               = 1
  max_instance_count               = 30
  max_instance_request_concurrency = 24
  timeout_seconds                  = 120
  cpu                              = "2"
  memory                           = "3Gi"
  cpu_idle                         = false
  startup_cpu_boost                = true
}
