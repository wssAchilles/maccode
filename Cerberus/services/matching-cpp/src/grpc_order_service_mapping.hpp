#pragma once

#include <cstdint>
#include <string>

#include "cerberus/order/v1/order.pb.h"
#include "order_service.hpp"

struct GrpcServiceRuntimeStats {
  std::uint64_t submit_order_requests_total{0};
  std::uint64_t submit_order_errors_total{0};
  std::uint64_t submit_order_rejections_total{0};
  double submit_order_latency_p95_ms{0.0};
  double submit_order_throughput_rps{0.0};
  std::uint64_t inflight_requests{0};
  std::uint64_t inflight_requests_peak{0};
  std::uint64_t max_inflight_requests{0};
  std::uint64_t backpressure_waits_total{0};
  std::uint64_t backpressure_rejections_total{0};
  std::uint64_t backpressure_wait_timeouts_total{0};
  std::uint64_t backpressure_wait_ms_total{0};
  std::uint64_t execution_stream_limit{0};
  std::uint64_t submit_latency_window_size{0};
  std::uint64_t grpc_min_pollers{0};
  std::uint64_t grpc_max_pollers{0};
  std::uint64_t grpc_num_cqs{0};
};

void PopulateOrderBookResponse(const SymbolOrderBookView& view, std::uint64_t generated_at_ms,
                               cerberus::order::v1::GetOrderBookResponse* response);

void PopulateHealthResponse(bool degraded, const std::string& degraded_reason,
                            const std::string& service_version, std::uint64_t uptime_seconds,
                            cerberus::order::v1::HealthResponse* response);

void PopulateServiceStatsResponse(const ServiceStats& stats,
                                  const GrpcServiceRuntimeStats& runtime_stats, bool degraded,
                                  const std::string& degraded_reason, double uptime_seconds,
                                  cerberus::order::v1::GetServiceStatsResponse* response);
