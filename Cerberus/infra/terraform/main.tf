locals {
  name_prefix = "cerberus-${var.environment}"
  required_apis = toset([
    "run.googleapis.com",
    "container.googleapis.com",
    "artifactregistry.googleapis.com",
    "redis.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "compute.googleapis.com",
    "servicenetworking.googleapis.com",
    "vpcaccess.googleapis.com",
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

resource "google_compute_network" "vpc" {
  name                    = "${local.name_prefix}-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  name          = "${local.name_prefix}-subnet"
  ip_cidr_range = "10.30.0.0/24"
  region        = var.region
  network       = google_compute_network.vpc.id
}

resource "google_vpc_access_connector" "connector" {
  name          = "${local.name_prefix}-connector"
  region        = var.region
  network       = google_compute_network.vpc.name
  ip_cidr_range = "10.31.0.0/28"

  depends_on = [google_project_service.required]
}

resource "google_redis_instance" "market_bus" {
  name               = "${local.name_prefix}-redis"
  display_name       = "Cerberus Market Bus"
  tier               = "BASIC"
  memory_size_gb     = 1
  region             = var.region
  authorized_network = google_compute_network.vpc.id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"

  depends_on = [google_project_service.required]
}

resource "random_password" "db_password" {
  length  = 20
  special = true
}

resource "google_sql_database_instance" "core" {
  name             = "${local.name_prefix}-sql"
  region           = var.region
  database_version = "POSTGRES_16"

  settings {
    tier = "db-custom-2-7680"
    ip_configuration {
      ipv4_enabled = true
    }
  }

  deletion_protection = false

  depends_on = [google_project_service.required]
}

resource "google_sql_database" "app_db" {
  name     = "cerberus"
  instance = google_sql_database_instance.core.name
}

resource "google_sql_user" "app_user" {
  name     = "cerberus"
  instance = google_sql_database_instance.core.name
  password = random_password.db_password.result
}

resource "google_container_cluster" "matching" {
  name               = "${local.name_prefix}-gke"
  location           = var.region
  initial_node_count = 1

  network    = google_compute_network.vpc.id
  subnetwork = google_compute_subnetwork.subnet.id

  release_channel {
    channel = "REGULAR"
  }

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  deletion_protection = false

  depends_on = [google_project_service.required]
}

resource "google_container_node_pool" "matching_pool" {
  name       = "matching-pool"
  cluster    = google_container_cluster.matching.id
  location   = var.region
  node_count = 2

  node_config {
    machine_type = "c3-standard-4"
    tags         = ["matching-engine"]
  }
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

resource "google_cloud_run_v2_service" "gateway" {
  name     = "${local.name_prefix}-gateway"
  location = var.region

  template {
    containers {
      image = var.container_images.gateway
      env {
        name  = "REDIS_URL"
        value = "redis://${google_redis_instance.market_bus.host}:${google_redis_instance.market_bus.port}/0"
      }
    }
    vpc_access {
      connector = google_vpc_access_connector.connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }
  }
}

resource "google_cloud_run_v2_service" "strategy" {
  name     = "${local.name_prefix}-strategy"
  location = var.region

  template {
    containers {
      image = var.container_images.strategy

      env {
        name  = "REDIS_URL"
        value = "redis://${google_redis_instance.market_bus.host}:${google_redis_instance.market_bus.port}/0"
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
        value = "strategy_signals"
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
    vpc_access {
      connector = google_vpc_access_connector.connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }
  }
}

resource "google_cloud_run_v2_service" "frontend" {
  name     = "${local.name_prefix}-frontend"
  location = var.region

  template {
    containers {
      image = var.container_images.frontend
      env {
        name  = "VITE_FIREBASE_PROJECT_ID"
        value = var.firebase_project_id
      }
      env {
        name  = "VITE_FIREBASE_API_KEY"
        value = var.firebase_web_config.api_key
      }
      env {
        name  = "VITE_FIREBASE_AUTH_DOMAIN"
        value = var.firebase_web_config.auth_domain
      }
      env {
        name  = "VITE_FIREBASE_STORAGE_BUCKET"
        value = var.firebase_web_config.storage_bucket
      }
      env {
        name  = "VITE_FIREBASE_MESSAGING_SENDER_ID"
        value = var.firebase_web_config.messaging_sender_id
      }
      env {
        name  = "VITE_FIREBASE_APP_ID"
        value = var.firebase_web_config.app_id
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

resource "google_cloud_run_v2_service_iam_member" "frontend_public" {
  name     = google_cloud_run_v2_service.frontend.name
  location = google_cloud_run_v2_service.frontend.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}
