locals {
  name_prefix = "cerberus-${var.environment}"
  required_apis = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "iam.googleapis.com",
  ])
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

resource "google_cloud_run_v2_service" "strategy" {
  name     = "${local.name_prefix}-strategy"
  location = var.region
  depends_on = [
    google_project_iam_member.strategy_secret_accessor,
  ]

  template {
    service_account = google_service_account.strategy.email

    containers {
      image = var.container_images.strategy

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
        name  = "MATCHING_ENABLED"
        value = tostring(var.matching_enabled)
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
    service_account = google_service_account.gateway.email

    containers {
      image = var.container_images.gateway

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
    }
  }
}

resource "google_cloud_run_v2_service_iam_member" "gateway_public" {
  name     = google_cloud_run_v2_service.gateway.name
  location = google_cloud_run_v2_service.gateway.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "strategy_public" {
  name     = google_cloud_run_v2_service.strategy.name
  location = google_cloud_run_v2_service.strategy.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}
