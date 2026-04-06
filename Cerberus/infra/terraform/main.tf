locals {
  name_prefix   = "cerberus-${var.environment}"
  is_production = lower(var.environment) == "production"
  required_apis = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "iam.googleapis.com",
  ])
  required_secret_values = {
    gurobi_licenseid          = var.gurobi_licenseid
    gurobi_wlsaccessid        = var.gurobi_wlsaccessid
    gurobi_wlssecret          = var.gurobi_wlssecret
    upstash_redis_url         = var.upstash_redis_url
    upstash_redis_rest_url    = var.upstash_redis_rest_url
    upstash_redis_rest_token  = var.upstash_redis_rest_token
    supabase_project_url      = var.supabase_project_url
    supabase_anon_key         = var.supabase_anon_key
    supabase_service_role_key = var.supabase_service_role_key
    supabase_db_url           = var.supabase_db_url
    firebase_web_api_key      = var.firebase_web_api_key
    jwt_hs256_secret          = var.jwt_hs256_secret
    binance_api_key           = var.binance_api_key
    binance_api_secret        = var.binance_api_secret
    alpaca_api_key            = var.alpaca_api_key
    alpaca_api_secret         = var.alpaca_api_secret
  }
  empty_required_secret_keys = [
    for key, value in local.required_secret_values : key if length(trimspace(value)) == 0
  ]
}

resource "terraform_data" "policy_guardrails" {
  input = true

  lifecycle {
    precondition {
      condition     = length(local.empty_required_secret_keys) == 0
      error_message = "Required secret variables must be non-empty: ${join(", ", local.empty_required_secret_keys)}"
    }
    precondition {
      condition     = length(trimspace(var.jwt_hs256_secret)) > 0
      error_message = "jwt_hs256_secret must be non-empty."
    }
    precondition {
      condition     = !local.is_production || var.jwt_auth_require_in_production
      error_message = "jwt_auth_require_in_production must be true when environment=production."
    }
    precondition {
      condition     = !local.is_production || var.cors_allow_origins != "*"
      error_message = "cors_allow_origins cannot be '*' when environment=production."
    }
    precondition {
      condition     = !local.is_production || var.internal_services_ingress
      error_message = "internal_services_ingress must be true when environment=production."
    }
    precondition {
      condition     = !local.is_production || (!var.strategy_public_access && !var.matching_public_access)
      error_message = "strategy_public_access and matching_public_access must be false when environment=production."
    }
    precondition {
      condition     = !local.is_production || var.strategy_internal_auth_enabled
      error_message = "strategy_internal_auth_enabled must be true when environment=production."
    }
    precondition {
      condition     = !local.is_production || var.strategy_upstream_circuit_enabled
      error_message = "strategy_upstream_circuit_enabled must be true when environment=production."
    }
    precondition {
      condition     = !local.is_production || (var.redis_order_events_stream_enabled && var.market_stream_enabled)
      error_message = "redis_order_events_stream_enabled and market_stream_enabled must both be true when environment=production."
    }
    precondition {
      condition = (
        !local.is_production || (
          !var.market_stream_legacy_pubsub_fallback &&
          !var.redis_market_events_publish_legacy_pubsub &&
          !var.redis_order_events_legacy_pubsub_fallback
        )
      )
      error_message = "market_stream_legacy_pubsub_fallback, redis_market_events_publish_legacy_pubsub, and redis_order_events_legacy_pubsub_fallback must be false when environment=production."
    }
    precondition {
      condition     = !local.is_production || var.cloud_run_gateway.min_instance_count >= 1
      error_message = "cloud_run_gateway.min_instance_count must be >= 1 when environment=production."
    }
    precondition {
      condition     = !local.is_production || var.cloud_run_strategy.min_instance_count >= 1
      error_message = "cloud_run_strategy.min_instance_count must be >= 1 when environment=production."
    }
    precondition {
      condition     = !local.is_production || var.cloud_run_matching.min_instance_count >= 1
      error_message = "cloud_run_matching.min_instance_count must be >= 1 when environment=production."
    }
    precondition {
      condition = (
        var.matching_grpc_min_pollers >= 1 &&
        var.matching_grpc_max_pollers >= var.matching_grpc_min_pollers &&
        var.matching_grpc_num_cqs >= 1 &&
        var.matching_grpc_num_cqs <= var.matching_grpc_max_pollers
      )
      error_message = "matching_grpc_* must satisfy: min>=1, max>=min, 1<=num_cqs<=max."
    }
  }
}

resource "google_project_service" "required" {
  for_each           = local.required_apis
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "containers" {
  location      = var.region
  repository_id = "cerberus"
  description   = "Cerberus service images"
  format        = "DOCKER"

  depends_on = [google_project_service.required]
}

resource "google_service_account" "gateway" {
  account_id   = "${local.name_prefix}-gateway-sa"
  display_name = "Cerberus Gateway Runtime"
}

resource "google_service_account" "strategy" {
  account_id   = "${local.name_prefix}-strategy-sa"
  display_name = "Cerberus Strategy Runtime"
}

resource "google_service_account" "matching" {
  account_id   = "${local.name_prefix}-matching-sa"
  display_name = "Cerberus Matching Runtime"
}

resource "google_project_iam_member" "gateway_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.gateway.email}"
}

resource "google_project_iam_member" "strategy_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.strategy.email}"
}

resource "google_secret_manager_secret" "gurobi_licenseid" {
  secret_id = "${local.name_prefix}-gurobi-licenseid"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "gurobi_licenseid_v1" {
  secret      = google_secret_manager_secret.gurobi_licenseid.id
  secret_data = var.gurobi_licenseid
}

resource "google_secret_manager_secret" "gurobi_wlsaccessid" {
  secret_id = "${local.name_prefix}-gurobi-wlsaccessid"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "gurobi_wlsaccessid_v1" {
  secret      = google_secret_manager_secret.gurobi_wlsaccessid.id
  secret_data = var.gurobi_wlsaccessid
}

resource "google_secret_manager_secret" "gurobi_wlssecret" {
  secret_id = "${local.name_prefix}-gurobi-wlssecret"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "gurobi_wlssecret_v1" {
  secret      = google_secret_manager_secret.gurobi_wlssecret.id
  secret_data = var.gurobi_wlssecret
}

resource "google_secret_manager_secret" "upstash_redis_url" {
  secret_id = "${local.name_prefix}-upstash-redis-url"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "upstash_redis_url_v1" {
  secret      = google_secret_manager_secret.upstash_redis_url.id
  secret_data = var.upstash_redis_url
}

resource "google_secret_manager_secret" "upstash_redis_rest_url" {
  secret_id = "${local.name_prefix}-upstash-redis-rest-url"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "upstash_redis_rest_url_v1" {
  secret      = google_secret_manager_secret.upstash_redis_rest_url.id
  secret_data = var.upstash_redis_rest_url
}

resource "google_secret_manager_secret" "upstash_redis_rest_token" {
  secret_id = "${local.name_prefix}-upstash-redis-rest-token"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "upstash_redis_rest_token_v1" {
  secret      = google_secret_manager_secret.upstash_redis_rest_token.id
  secret_data = var.upstash_redis_rest_token
}

resource "google_secret_manager_secret" "supabase_project_url" {
  secret_id = "${local.name_prefix}-supabase-project-url"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "supabase_project_url_v1" {
  secret      = google_secret_manager_secret.supabase_project_url.id
  secret_data = var.supabase_project_url
}

resource "google_secret_manager_secret" "supabase_anon_key" {
  secret_id = "${local.name_prefix}-supabase-anon-key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "supabase_anon_key_v1" {
  secret      = google_secret_manager_secret.supabase_anon_key.id
  secret_data = var.supabase_anon_key
}

resource "google_secret_manager_secret" "supabase_service_role_key" {
  secret_id = "${local.name_prefix}-supabase-service-role-key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "supabase_service_role_key_v1" {
  secret      = google_secret_manager_secret.supabase_service_role_key.id
  secret_data = var.supabase_service_role_key
}

resource "google_secret_manager_secret" "supabase_db_url" {
  secret_id = "${local.name_prefix}-supabase-db-url"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "supabase_db_url_v1" {
  secret      = google_secret_manager_secret.supabase_db_url.id
  secret_data = var.supabase_db_url
}

resource "google_secret_manager_secret" "firebase_web_api_key" {
  secret_id = "${local.name_prefix}-firebase-web-api-key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "firebase_web_api_key_v1" {
  secret      = google_secret_manager_secret.firebase_web_api_key.id
  secret_data = var.firebase_web_api_key
}

resource "google_secret_manager_secret" "jwt_hs256_secret" {
  secret_id = "${local.name_prefix}-jwt-hs256-secret"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "jwt_hs256_secret_v1" {
  secret      = google_secret_manager_secret.jwt_hs256_secret.id
  secret_data = var.jwt_hs256_secret
}

resource "google_secret_manager_secret" "binance_api_key" {
  secret_id = "${local.name_prefix}-binance-api-key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "binance_api_key_v1" {
  secret      = google_secret_manager_secret.binance_api_key.id
  secret_data = var.binance_api_key
}

resource "google_secret_manager_secret" "binance_api_secret" {
  secret_id = "${local.name_prefix}-binance-api-secret"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "binance_api_secret_v1" {
  secret      = google_secret_manager_secret.binance_api_secret.id
  secret_data = var.binance_api_secret
}

resource "google_secret_manager_secret" "alpaca_api_key" {
  secret_id = "${local.name_prefix}-alpaca-api-key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "alpaca_api_key_v1" {
  secret      = google_secret_manager_secret.alpaca_api_key.id
  secret_data = var.alpaca_api_key
}

resource "google_secret_manager_secret" "alpaca_api_secret" {
  secret_id = "${local.name_prefix}-alpaca-api-secret"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "alpaca_api_secret_v1" {
  secret      = google_secret_manager_secret.alpaca_api_secret.id
  secret_data = var.alpaca_api_secret
}

resource "google_cloud_run_v2_service" "matching" {
  name     = "${local.name_prefix}-matching"
  location = var.region
  ingress  = var.internal_services_ingress ? "INGRESS_TRAFFIC_INTERNAL_ONLY" : "INGRESS_TRAFFIC_ALL"

  template {
    service_account                  = google_service_account.matching.email
    timeout                          = "${var.cloud_run_matching.timeout_seconds}s"
    max_instance_request_concurrency = var.cloud_run_matching.max_instance_request_concurrency

    scaling {
      min_instance_count = var.cloud_run_matching.min_instance_count
      max_instance_count = var.cloud_run_matching.max_instance_count
    }

    containers {
      image = coalesce(var.container_images.matching, "asia-east2-docker.pkg.dev/cerberus-9d94f/cerberus/matching:latest")

      ports {
        container_port = 8080
      }
      resources {
        limits = {
          cpu    = var.cloud_run_matching.cpu
          memory = var.cloud_run_matching.memory
        }
        cpu_idle          = var.cloud_run_matching.cpu_idle
        startup_cpu_boost = var.cloud_run_matching.startup_cpu_boost
      }
      env {
        name  = "MATCHING_GRPC_MAX_POLLERS"
        value = tostring(var.matching_grpc_max_pollers)
      }
      env {
        name  = "MATCHING_GRPC_MIN_POLLERS"
        value = tostring(var.matching_grpc_min_pollers)
      }
      env {
        name  = "MATCHING_GRPC_NUM_CQS"
        value = tostring(var.matching_grpc_num_cqs)
      }
      env {
        name  = "MATCHING_EXECUTION_STREAM_LIMIT"
        value = tostring(var.matching_execution_stream_limit)
      }
      env {
        name  = "MATCHING_SUBMIT_LATENCY_WINDOW_SIZE"
        value = tostring(var.matching_submit_latency_window_size)
      }
      env {
        name  = "MATCHING_MAX_INFLIGHT_REQUESTS"
        value = tostring(var.matching_max_inflight_requests)
      }
      env {
        name  = "MATCHING_INFLIGHT_ACQUIRE_TIMEOUT_MS"
        value = tostring(var.matching_inflight_acquire_timeout_ms)
      }
      env {
        name  = "MATCHING_BACKPRESSURE_RETRY_SLEEP_MS"
        value = tostring(var.matching_backpressure_retry_sleep_ms)
      }
    }
  }
}

resource "google_cloud_run_v2_service" "strategy" {
  name     = "${local.name_prefix}-strategy"
  location = var.region
  ingress  = var.internal_services_ingress ? "INGRESS_TRAFFIC_INTERNAL_ONLY" : "INGRESS_TRAFFIC_ALL"
  depends_on = [
    google_project_iam_member.strategy_secret_accessor,
  ]

  template {
    service_account                  = google_service_account.strategy.email
    timeout                          = "${var.cloud_run_strategy.timeout_seconds}s"
    max_instance_request_concurrency = var.cloud_run_strategy.max_instance_request_concurrency

    scaling {
      min_instance_count = var.cloud_run_strategy.min_instance_count
      max_instance_count = var.cloud_run_strategy.max_instance_count
    }

    containers {
      image = var.container_images.strategy
      resources {
        limits = {
          cpu    = var.cloud_run_strategy.cpu
          memory = var.cloud_run_strategy.memory
        }
        cpu_idle          = var.cloud_run_strategy.cpu_idle
        startup_cpu_boost = var.cloud_run_strategy.startup_cpu_boost
      }

      env {
        name = "REDIS_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.upstash_redis_url.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "UPSTASH_REDIS_REST_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.upstash_redis_rest_url.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "UPSTASH_REDIS_REST_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.upstash_redis_rest_token.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "SUPABASE_PROJECT_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.supabase_project_url.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "SUPABASE_ANON_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.supabase_anon_key.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "SUPABASE_SERVICE_ROLE_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.supabase_service_role_key.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "SUPABASE_DB_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.supabase_db_url.secret_id
            version = "latest"
          }
        }
      }
      env {
        name  = "SUPABASE_ENABLED"
        value = tostring(var.supabase_enabled)
      }
      env {
        name  = "FIREBASE_ENABLED"
        value = tostring(var.firebase_enabled)
      }
      env {
        name  = "FIREBASE_PROJECT_ID"
        value = var.firebase_project_id
      }
      env {
        name  = "FIREBASE_SIGNAL_COLLECTION"
        value = var.firebase_signal_collection
      }
      env {
        name  = "CORS_ALLOW_ORIGINS"
        value = var.cors_allow_origins
      }
      env {
        name  = "APP_ENV"
        value = var.environment
      }
      env {
        name  = "MATCHING_ENABLED"
        value = tostring(var.matching_enabled)
      }
      env {
        name  = "MATCHING_GRPC_TARGET"
        value = google_cloud_run_v2_service.matching.uri
      }
      env {
        name  = "MARKET_STREAM_ENABLED"
        value = tostring(var.market_stream_enabled)
      }
      env {
        name  = "MARKET_STREAM_KEY"
        value = var.redis_market_events_stream_key
      }
      env {
        name  = "MARKET_STREAM_CONSUMER_GROUP"
        value = var.market_stream_consumer_group
      }
      env {
        name  = "MARKET_STREAM_READ_BLOCK_MS"
        value = tostring(var.market_stream_read_block_ms)
      }
      env {
        name  = "MARKET_STREAM_RECLAIM_ENABLED"
        value = tostring(var.market_stream_reclaim_enabled)
      }
      env {
        name  = "MARKET_STREAM_RECLAIM_INTERVAL_MS"
        value = tostring(var.market_stream_reclaim_interval_ms)
      }
      env {
        name  = "MARKET_STREAM_RECLAIM_IDLE_MS"
        value = tostring(var.market_stream_reclaim_idle_ms)
      }
      env {
        name  = "MARKET_STREAM_RECLAIM_BATCH_SIZE"
        value = tostring(var.market_stream_reclaim_batch_size)
      }
      env {
        name  = "MARKET_STREAM_MAX_DELIVERY_ATTEMPTS"
        value = tostring(var.market_stream_max_delivery_attempts)
      }
      env {
        name  = "MARKET_STREAM_PENDING_WARN_THRESHOLD"
        value = tostring(var.market_stream_pending_warn_threshold)
      }
      env {
        name  = "MARKET_STREAM_LAG_WARN_THRESHOLD"
        value = tostring(var.market_stream_lag_warn_threshold)
      }
      env {
        name  = "MARKET_STREAM_POISON_STREAM_KEY"
        value = var.market_stream_poison_stream_key
      }
      env {
        name  = "MARKET_STREAM_POISON_STREAM_MAXLEN"
        value = tostring(var.market_stream_poison_stream_maxlen)
      }
      env {
        name  = "MARKET_STREAM_LEGACY_PUBSUB_FALLBACK"
        value = tostring(var.market_stream_legacy_pubsub_fallback)
      }
      env {
        name  = "EVENT_STREAM_ENABLED"
        value = tostring(var.redis_order_events_stream_enabled)
      }
      env {
        name  = "EVENT_STREAM_KEY"
        value = var.redis_order_events_stream_key
      }
      env {
        name  = "EVENT_STREAM_MAXLEN"
        value = tostring(var.strategy_event_stream_maxlen)
      }
      env {
        name  = "EVENT_STREAM_PUBLISH_LEGACY_PUBSUB"
        value = tostring(var.redis_order_events_legacy_pubsub_fallback)
      }
      env {
        name  = "EXECUTION_RELAY_INTERVAL_SECONDS"
        value = tostring(var.execution_relay_interval_seconds)
      }

      env {
        name = "GRB_LICENSEID"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gurobi_licenseid.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "GRB_WLSACCESSID"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gurobi_wlsaccessid.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "GRB_WLSSECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gurobi_wlssecret.secret_id
            version = "latest"
          }
        }
      }
    }
  }
}

resource "google_cloud_run_v2_service" "gateway" {
  name     = "${local.name_prefix}-gateway"
  location = var.region
  depends_on = [
    google_project_iam_member.gateway_secret_accessor,
  ]

  template {
    service_account                  = google_service_account.gateway.email
    timeout                          = "${var.cloud_run_gateway.timeout_seconds}s"
    max_instance_request_concurrency = var.cloud_run_gateway.max_instance_request_concurrency

    scaling {
      min_instance_count = var.cloud_run_gateway.min_instance_count
      max_instance_count = var.cloud_run_gateway.max_instance_count
    }

    containers {
      image = var.container_images.gateway
      resources {
        limits = {
          cpu    = var.cloud_run_gateway.cpu
          memory = var.cloud_run_gateway.memory
        }
        cpu_idle          = var.cloud_run_gateway.cpu_idle
        startup_cpu_boost = var.cloud_run_gateway.startup_cpu_boost
      }

      env {
        name = "REDIS_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.upstash_redis_url.secret_id
            version = "latest"
          }
        }
      }
      env {
        name  = "STRATEGY_BASE_URL"
        value = google_cloud_run_v2_service.strategy.uri
      }
      env {
        name  = "STRATEGY_INTERNAL_AUTH_ENABLED"
        value = tostring(var.strategy_internal_auth_enabled)
      }
      env {
        name  = "STRATEGY_INTERNAL_AUTH_AUDIENCE"
        value = google_cloud_run_v2_service.strategy.uri
      }
      env {
        name  = "STRATEGY_INTERNAL_AUTH_TOKEN_TTL_SECONDS"
        value = tostring(var.strategy_internal_auth_token_ttl_seconds)
      }
      env {
        name  = "GCP_METADATA_IDENTITY_URL"
        value = var.strategy_internal_auth_metadata_identity_url
      }
      env {
        name  = "STRATEGY_UPSTREAM_TIMEOUT_MS"
        value = tostring(var.strategy_upstream_timeout_ms)
      }
      env {
        name  = "STRATEGY_UPSTREAM_HEALTH_TIMEOUT_MS"
        value = tostring(var.strategy_upstream_health_timeout_ms)
      }
      env {
        name  = "STRATEGY_UPSTREAM_MAX_INFLIGHT"
        value = tostring(var.strategy_upstream_max_inflight)
      }
      env {
        name  = "STRATEGY_UPSTREAM_QUEUE_TIMEOUT_MS"
        value = tostring(var.strategy_upstream_queue_timeout_ms)
      }
      env {
        name  = "STRATEGY_UPSTREAM_CIRCUIT_ENABLED"
        value = tostring(var.strategy_upstream_circuit_enabled)
      }
      env {
        name  = "STRATEGY_UPSTREAM_CIRCUIT_FAILURE_THRESHOLD"
        value = tostring(var.strategy_upstream_circuit_failure_threshold)
      }
      env {
        name  = "STRATEGY_UPSTREAM_CIRCUIT_OPEN_MS"
        value = tostring(var.strategy_upstream_circuit_open_ms)
      }
      env {
        name  = "STRATEGY_SUMMARY_CACHE_TTL_MS"
        value = tostring(var.strategy_summary_cache_ttl_ms)
      }
      env {
        name  = "STRATEGY_SUMMARY_BATCH_WINDOW_MS"
        value = tostring(var.strategy_summary_batch_window_ms)
      }
      env {
        name  = "APP_ENV"
        value = var.environment
      }
      env {
        name  = "CORS_ALLOW_ORIGINS"
        value = var.cors_allow_origins
      }
      env {
        name  = "FIREBASE_AUTH_REQUIRED"
        value = tostring(var.firebase_auth_required)
      }
      env {
        name  = "FIREBASE_PROJECT_ID"
        value = var.firebase_project_id
      }
      env {
        name  = "JWT_AUTH_ENABLED"
        value = tostring(var.jwt_auth_enabled)
      }
      env {
        name  = "JWT_AUTH_REQUIRE_IN_PRODUCTION"
        value = tostring(var.jwt_auth_require_in_production)
      }
      env {
        name  = "JWT_ISSUER"
        value = var.jwt_issuer
      }
      env {
        name  = "JWT_AUDIENCE"
        value = var.jwt_audience
      }
      env {
        name = "JWT_HS256_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.jwt_hs256_secret.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "FIREBASE_WEB_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.firebase_web_api_key.secret_id
            version = "latest"
          }
        }
      }
      env {
        name  = "BINANCE_API_BASE"
        value = var.binance_api_base
      }
      env {
        name = "BINANCE_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.binance_api_key.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "BINANCE_API_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.binance_api_secret.secret_id
            version = "latest"
          }
        }
      }
      env {
        name  = "BINANCE_ORDER_TEST_PATH"
        value = var.binance_order_test_path
      }
      env {
        name  = "KLINE_API_URL"
        value = var.kline_api_url
      }
      env {
        name  = "TRADING_POLICY_ENFORCED"
        value = tostring(var.trading_policy_enforced)
      }
      env {
        name  = "BINANCE_ALLOWED_SYMBOLS"
        value = var.binance_allowed_symbols
      }
      env {
        name  = "ALPACA_ALLOWED_SYMBOLS"
        value = var.alpaca_allowed_symbols
      }
      env {
        name  = "MAX_BINANCE_ORDER_QTY"
        value = tostring(var.max_binance_order_qty)
      }
      env {
        name  = "MAX_BINANCE_ORDER_NOTIONAL_USD"
        value = tostring(var.max_binance_order_notional_usd)
      }
      env {
        name  = "MAX_ALPACA_ORDER_QTY"
        value = tostring(var.max_alpaca_order_qty)
      }
      env {
        name  = "MAX_ALPACA_LIMIT_NOTIONAL_USD"
        value = tostring(var.max_alpaca_limit_notional_usd)
      }
      env {
        name  = "ALPACA_TRADING_BASE_URL"
        value = var.alpaca_trading_base_url
      }
      env {
        name = "ALPACA_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.alpaca_api_key.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "ALPACA_API_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.alpaca_api_secret.secret_id
            version = "latest"
          }
        }
      }
      env {
        name  = "MARKET_SYMBOLS"
        value = var.market_symbols
      }
      env {
        name  = "REDIS_ORDER_EVENTS_CHANNELS"
        value = var.redis_order_events_channels
      }
      env {
        name  = "REDIS_ORDER_EVENTS_STREAM_ENABLED"
        value = tostring(var.redis_order_events_stream_enabled)
      }
      env {
        name  = "REDIS_ORDER_EVENTS_LEGACY_PUBSUB_FALLBACK"
        value = tostring(var.redis_order_events_legacy_pubsub_fallback)
      }
      env {
        name  = "REDIS_ORDER_EVENTS_STREAM_KEY"
        value = var.redis_order_events_stream_key
      }
      env {
        name  = "REDIS_ORDER_EVENTS_CONSUMER_GROUP"
        value = var.redis_order_events_consumer_group
      }
      env {
        name  = "REDIS_ORDER_EVENTS_CONSUMER_NAME"
        value = var.redis_order_events_consumer_name
      }
      env {
        name  = "REDIS_ORDER_EVENTS_READ_BATCH_SIZE"
        value = tostring(var.redis_order_events_read_batch_size)
      }
      env {
        name  = "REDIS_ORDER_EVENTS_READ_BLOCK_MS"
        value = tostring(var.redis_order_events_read_block_ms)
      }
      env {
        name  = "REDIS_ORDER_EVENTS_PENDING_REPLAY_COUNT"
        value = tostring(var.redis_order_events_pending_replay_count)
      }
      env {
        name  = "REDIS_ORDER_EVENTS_BATCH_WINDOW_MS"
        value = tostring(var.redis_order_events_batch_window_ms)
      }
      env {
        name  = "REDIS_ORDER_EVENTS_MAX_RETRIES_BEFORE_FALLBACK"
        value = tostring(var.redis_order_events_max_retries_before_fallback)
      }
      env {
        name  = "REDIS_ORDER_EVENTS_RETRY_BACKOFF_MS"
        value = tostring(var.redis_order_events_retry_backoff_ms)
      }
      env {
        name  = "REDIS_ORDER_EVENTS_RETRY_BACKOFF_MAX_MS"
        value = tostring(var.redis_order_events_retry_backoff_max_ms)
      }
      env {
        name  = "REDIS_ORDER_EVENTS_RECLAIM_ENABLED"
        value = tostring(var.redis_order_events_reclaim_enabled)
      }
      env {
        name  = "REDIS_ORDER_EVENTS_RECLAIM_INTERVAL_MS"
        value = tostring(var.redis_order_events_reclaim_interval_ms)
      }
      env {
        name  = "REDIS_ORDER_EVENTS_RECLAIM_IDLE_MS"
        value = tostring(var.redis_order_events_reclaim_idle_ms)
      }
      env {
        name  = "REDIS_ORDER_EVENTS_RECLAIM_BATCH_SIZE"
        value = tostring(var.redis_order_events_reclaim_batch_size)
      }
      env {
        name  = "REDIS_ORDER_EVENTS_MAX_DELIVERY_ATTEMPTS"
        value = tostring(var.redis_order_events_max_delivery_attempts)
      }
      env {
        name  = "REDIS_ORDER_EVENTS_POISON_STREAM_KEY"
        value = var.redis_order_events_poison_stream_key
      }
      env {
        name  = "REDIS_ORDER_EVENTS_POISON_STREAM_MAXLEN"
        value = tostring(var.redis_order_events_poison_stream_maxlen)
      }
      env {
        name  = "REDIS_ORDER_EVENTS_PENDING_WARN_THRESHOLD"
        value = tostring(var.redis_order_events_pending_warn_threshold)
      }
      env {
        name  = "REDIS_ORDER_EVENTS_LAG_WARN_THRESHOLD"
        value = tostring(var.redis_order_events_lag_warn_threshold)
      }
      env {
        name  = "REDIS_ORDERBOOK_CHANNEL"
        value = var.redis_orderbook_channel
      }
      env {
        name  = "REDIS_ORDERBOOK_CHANNEL_PREFIX"
        value = var.redis_orderbook_channel_prefix
      }
      env {
        name  = "REDIS_TICK_CHANNEL_PREFIX"
        value = var.redis_tick_channel_prefix
      }
      env {
        name  = "REDIS_MARKET_EVENTS_STREAM_ENABLED"
        value = tostring(var.redis_market_events_stream_enabled)
      }
      env {
        name  = "REDIS_MARKET_EVENTS_STREAM_KEY"
        value = var.redis_market_events_stream_key
      }
      env {
        name  = "REDIS_MARKET_EVENTS_STREAM_MAXLEN"
        value = tostring(var.redis_market_events_stream_maxlen)
      }
      env {
        name  = "REDIS_MARKET_EVENTS_PUBLISH_LEGACY_PUBSUB"
        value = tostring(var.redis_market_events_publish_legacy_pubsub)
      }
      env {
        name  = "REDIS_MARKET_EVENTS_SINGLE_WRITER_ENABLED"
        value = tostring(var.redis_market_events_single_writer_enabled)
      }
      env {
        name  = "REDIS_MARKET_EVENTS_LEADER_LOCK_KEY"
        value = var.redis_market_events_leader_lock_key
      }
      env {
        name  = "REDIS_MARKET_EVENTS_LEADER_TTL_MS"
        value = tostring(var.redis_market_events_leader_ttl_ms)
      }
      env {
        name  = "REDIS_MARKET_EVENTS_LEADER_HEARTBEAT_MS"
        value = tostring(var.redis_market_events_leader_heartbeat_ms)
      }
      env {
        name  = "REDIS_MARKET_EVENTS_MIN_PUBLISH_INTERVAL_MS"
        value = tostring(var.redis_market_events_min_publish_interval_ms)
      }
      env {
        name  = "REDIS_MARKET_EVENTS_PUBLISH_ON_PRICE_CHANGE_ONLY"
        value = tostring(var.redis_market_events_publish_on_price_change_only)
      }
      env {
        name  = "CERBERUS_EVENT_SCHEMA_VERSION"
        value = "v1"
      }
    }
  }
}

resource "google_cloud_run_v2_service_iam_member" "gateway_public" {
  count    = var.gateway_public_access ? 1 : 0
  name     = google_cloud_run_v2_service.gateway.name
  location = google_cloud_run_v2_service.gateway.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "strategy_invoked_by_gateway" {
  name     = google_cloud_run_v2_service.strategy.name
  location = google_cloud_run_v2_service.strategy.location
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.gateway.email}"
}

resource "google_cloud_run_v2_service_iam_member" "matching_invoked_by_strategy" {
  name     = google_cloud_run_v2_service.matching.name
  location = google_cloud_run_v2_service.matching.location
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.strategy.email}"
}

resource "google_cloud_run_v2_service_iam_member" "strategy_public" {
  count    = var.strategy_public_access ? 1 : 0
  name     = google_cloud_run_v2_service.strategy.name
  location = google_cloud_run_v2_service.strategy.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "matching_public" {
  count    = var.matching_public_access ? 1 : 0
  name     = google_cloud_run_v2_service.matching.name
  location = google_cloud_run_v2_service.matching.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}
