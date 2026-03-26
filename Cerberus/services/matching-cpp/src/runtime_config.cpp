#include "runtime_config.hpp"

#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <iostream>

namespace {

int ReadBoundedIntEnv(const char* key, int default_value, int min_value, int max_value) {
  const char* raw = std::getenv(key);
  if (raw == nullptr || *raw == '\0') {
    return default_value;
  }
  try {
    const int parsed = std::stoi(std::string(raw));
    if (parsed < min_value || parsed > max_value) {
      std::cerr << "env " << key << "=" << raw << " out of range [" << min_value << ", "
                << max_value << "], clamped to " << std::clamp(parsed, min_value, max_value)
                << std::endl;
    }
    return std::clamp(parsed, min_value, max_value);
  } catch (...) {
    std::cerr << "env " << key << "=" << raw << " invalid, fallback to " << default_value
              << std::endl;
    return default_value;
  }
}

std::size_t ReadBoundedSizeEnv(const char* key, std::size_t default_value, std::size_t min_value,
                               std::size_t max_value) {
  const char* raw = std::getenv(key);
  if (raw == nullptr || *raw == '\0') {
    return default_value;
  }
  try {
    const auto parsed = static_cast<std::size_t>(std::stoull(std::string(raw)));
    if (parsed < min_value || parsed > max_value) {
      std::cerr << "env " << key << "=" << raw << " out of range [" << min_value << ", "
                << max_value << "], clamped to " << std::clamp(parsed, min_value, max_value)
                << std::endl;
    }
    return std::clamp(parsed, min_value, max_value);
  } catch (...) {
    std::cerr << "env " << key << "=" << raw << " invalid, fallback to " << default_value
              << std::endl;
    return default_value;
  }
}

std::uint64_t ReadBoundedU64Env(const char* key, std::uint64_t default_value,
                                std::uint64_t min_value, std::uint64_t max_value) {
  const char* raw = std::getenv(key);
  if (raw == nullptr || *raw == '\0') {
    return default_value;
  }
  try {
    const auto parsed = static_cast<std::uint64_t>(std::stoull(std::string(raw)));
    if (parsed < min_value || parsed > max_value) {
      std::cerr << "env " << key << "=" << raw << " out of range [" << min_value << ", "
                << max_value << "], clamped to " << std::clamp(parsed, min_value, max_value)
                << std::endl;
    }
    return std::clamp(parsed, min_value, max_value);
  } catch (...) {
    std::cerr << "env " << key << "=" << raw << " invalid, fallback to " << default_value
              << std::endl;
    return default_value;
  }
}

}  // namespace

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
            << ", inflight_acquire_timeout_ms=" << cfg.inflight_acquire_timeout_ms << std::endl;
}
