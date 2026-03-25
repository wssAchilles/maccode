output "artifact_registry_repository" {
  value = google_artifact_registry_repository.containers.name
}

output "cloud_run_gateway_url" {
  value = google_cloud_run_v2_service.gateway.uri
}

output "cloud_run_strategy_url" {
  value = google_cloud_run_v2_service.strategy.uri
}

output "cloud_run_matching_url" {
  value = google_cloud_run_v2_service.matching.uri
}
