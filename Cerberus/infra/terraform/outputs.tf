output "artifact_registry_repository" {
  value = google_artifact_registry_repository.containers.name
}

output "redis_endpoint" {
  value = "${google_redis_instance.market_bus.host}:${google_redis_instance.market_bus.port}"
}

output "cloud_sql_connection_name" {
  value = google_sql_database_instance.core.connection_name
}

output "cloud_run_gateway_url" {
  value = google_cloud_run_v2_service.gateway.uri
}

output "cloud_run_strategy_url" {
  value = google_cloud_run_v2_service.strategy.uri
}

output "cloud_run_frontend_url" {
  value = google_cloud_run_v2_service.frontend.uri
}

output "gke_cluster_name" {
  value = google_container_cluster.matching.name
}

