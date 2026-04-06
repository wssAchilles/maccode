environment = "production"

firebase_enabled               = true
supabase_enabled               = true
matching_enabled               = true
firebase_auth_required         = true
jwt_auth_enabled               = true
jwt_auth_require_in_production = true

internal_services_ingress            = true
strategy_public_access               = false
matching_public_access               = false
gateway_public_access                = true
matching_max_inflight_requests       = 2048
matching_inflight_acquire_timeout_ms = 40
matching_backpressure_retry_sleep_ms = 1
strategy_event_stream_maxlen         = 50000
strategy_summary_cache_ttl_ms        = 1200
strategy_summary_batch_window_ms     = 80

strategy_internal_auth_enabled              = true
strategy_upstream_circuit_enabled           = true
strategy_upstream_circuit_failure_threshold = 5
strategy_upstream_circuit_open_ms           = 20000

market_stream_legacy_pubsub_fallback        = false
redis_market_events_publish_legacy_pubsub   = false
redis_order_events_legacy_pubsub_fallback   = false
redis_market_events_single_writer_enabled   = true
redis_market_events_min_publish_interval_ms = 100

cloud_run_gateway = {
  min_instance_count               = 2
  max_instance_count               = 80
  max_instance_request_concurrency = 100
  timeout_seconds                  = 900
  cpu                              = "2"
  memory                           = "2Gi"
  cpu_idle                         = false
  startup_cpu_boost                = true
}

cloud_run_strategy = {
  min_instance_count               = 2
  max_instance_count               = 60
  max_instance_request_concurrency = 40
  timeout_seconds                  = 300
  cpu                              = "4"
  memory                           = "4Gi"
  cpu_idle                         = false
  startup_cpu_boost                = true
}

cloud_run_matching = {
  min_instance_count               = 2
  max_instance_count               = 60
  max_instance_request_concurrency = 32
  timeout_seconds                  = 120
  cpu                              = "4"
  memory                           = "4Gi"
  cpu_idle                         = false
  startup_cpu_boost                = true
}
