#include "runtime_config.hpp"
#include "runtime_env.hpp"

#include <algorithm>
#include <cstdlib>
#include <iostream>

std::string ResolveListenAddress() {
  const char* port_env = std::getenv("PORT");
  const std::string port = (port_env != nullptr && *port_env != '\0') ? port_env : "50051";
  return "0.0.0.0:" + port;
}

GrpcRuntimeConfig BuildRuntimeConfigFromEnv() {
  GrpcRuntimeConfig cfg{};
  cfg.max_pollers = ReadBoundedIntEnv("MATCHING_GRPC_MAX_POLLERS", 8, 1, 128);
  const int min_poller_default = std::max(1, cfg.max_pollers / 2);
  cfg.min_pollers =
      ReadBoundedIntEnv("MATCHING_GRPC_MIN_POLLERS", min_poller_default, 1, cfg.max_pollers);
  const int num_cqs_default = std::max(1, cfg.max_pollers / 2);
  cfg.num_cqs = ReadBoundedIntEnv("MATCHING_GRPC_NUM_CQS", num_cqs_default, 1, cfg.max_pollers);
  cfg.execution_stream_limit =
      ReadBoundedSizeEnv("MATCHING_EXECUTION_STREAM_LIMIT", 500, 1, 200000);
  cfg.submit_latency_window_size =
      ReadBoundedSizeEnv("MATCHING_SUBMIT_LATENCY_WINDOW_SIZE", 1024, 32, 1000000);
  cfg.max_inflight_requests =
      ReadBoundedSizeEnv("MATCHING_MAX_INFLIGHT_REQUESTS", 512, 1, 1000000);
  cfg.inflight_acquire_timeout_ms =
      ReadBoundedU64Env("MATCHING_INFLIGHT_ACQUIRE_TIMEOUT_MS", 25, 0, 60000);
  cfg.backpressure_retry_sleep_ms =
      ReadBoundedU64Env("MATCHING_BACKPRESSURE_RETRY_SLEEP_MS", 1, 0, 1000);
  return cfg;
}

void ConfigureSyncServerBuilder(grpc::ServerBuilder* builder, const GrpcRuntimeConfig& cfg) {
  if (builder == nullptr) {
    return;
  }
  builder->SetSyncServerOption(grpc::ServerBuilder::SyncServerOption::MIN_POLLERS, cfg.min_pollers);
  builder->SetSyncServerOption(grpc::ServerBuilder::SyncServerOption::MAX_POLLERS, cfg.max_pollers);
  builder->SetSyncServerOption(grpc::ServerBuilder::SyncServerOption::NUM_CQS, cfg.num_cqs);
}

void LogRuntimeConfig(const std::string& listen_addr, const GrpcRuntimeConfig& cfg) {
  std::cout << "Cerberus matching gRPC server runtime config: listen_addr=" << listen_addr
            << ", min_pollers=" << cfg.min_pollers << ", max_pollers=" << cfg.max_pollers
            << ", num_cqs=" << cfg.num_cqs
            << ", execution_stream_limit=" << cfg.execution_stream_limit
            << ", submit_latency_window_size=" << cfg.submit_latency_window_size
            << ", max_inflight_requests=" << cfg.max_inflight_requests
            << ", inflight_acquire_timeout_ms=" << cfg.inflight_acquire_timeout_ms
            << ", backpressure_retry_sleep_ms=" << cfg.backpressure_retry_sleep_ms << std::endl;
}
