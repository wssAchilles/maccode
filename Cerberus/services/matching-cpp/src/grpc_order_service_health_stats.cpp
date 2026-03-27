#include "grpc_order_service.hpp"
#include "grpc_order_service_mapping.hpp"

#include <algorithm>
#include <chrono>

#include "grpc_request_logging.hpp"

grpc::Status GrpcOrderService::Health(grpc::ServerContext* context,
                                      const cerberus::order::v1::HealthRequest* /*request*/,
                                      cerberus::order::v1::HealthResponse* response) {
  LogRequestStart("Health", context);
  EchoRequestId(context);
  FillResponseContext(context, "", "", response->mutable_schema_version(),
                      response->mutable_correlation_id());
  const bool degraded = IsDegraded();
  const std::string degraded_reason = degraded ? DegradedStatusText() : "";
  if (degraded) {
    MarkDegraded(context, degraded_reason);
  }
  PopulateHealthResponse(degraded, degraded_reason, service_version_, UptimeSeconds(), response);
  return grpc::Status::OK;
}

grpc::Status GrpcOrderService::GetServiceStats(
    grpc::ServerContext* context, const cerberus::order::v1::GetServiceStatsRequest* /*request*/,
    cerberus::order::v1::GetServiceStatsResponse* response) {
  LogRequestStart("GetServiceStats", context);
  EchoRequestId(context);
  FillResponseContext(context, "", "", response->mutable_schema_version(),
                      response->mutable_correlation_id());
  const bool degraded = IsDegraded();
  const std::string degraded_reason = degraded ? DegradedStatusText() : "";
  if (degraded) {
    MarkDegraded(context, degraded_reason);
  }
  ServiceStats stats;
  {
    std::scoped_lock<std::mutex> lock(mu_);
    stats = service_.Stats();
  }
  PopulateServiceStatsResponse(
      stats,
      GrpcServiceRuntimeStats{
          .submit_order_requests_total = submit_order_requests_total_.load(),
          .submit_order_errors_total = submit_order_errors_total_.load(),
          .submit_order_rejections_total = submit_order_rejections_total_.load(),
          .submit_order_latency_p95_ms = SubmitOrderLatencyP95Ms(),
          .submit_order_throughput_rps = SubmitOrderThroughputRps(),
          .inflight_requests = inflight_requests_.load(),
          .inflight_requests_peak = inflight_requests_peak_.load(),
          .max_inflight_requests = static_cast<std::uint64_t>(max_inflight_requests_),
          .backpressure_waits_total = backpressure_waits_total_.load(),
          .backpressure_rejections_total = backpressure_rejections_total_.load(),
          .backpressure_wait_timeouts_total = backpressure_wait_timeouts_total_.load(),
          .backpressure_wait_ms_total = backpressure_wait_ms_total_.load(),
          .execution_stream_limit = static_cast<std::uint64_t>(execution_stream_limit_),
          .submit_latency_window_size = static_cast<std::uint64_t>(submit_latency_window_size_),
          .grpc_min_pollers = static_cast<std::uint64_t>(std::max(grpc_min_pollers_, 1)),
          .grpc_max_pollers = static_cast<std::uint64_t>(std::max(grpc_max_pollers_, 1)),
          .grpc_num_cqs = static_cast<std::uint64_t>(std::max(grpc_num_cqs_, 1)),
      },
      degraded, degraded_reason, static_cast<double>(UptimeSeconds()), response);

  return grpc::Status::OK;
}
