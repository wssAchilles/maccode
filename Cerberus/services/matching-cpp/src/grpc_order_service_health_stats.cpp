#include "grpc_order_service.hpp"

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
  const auto uptime = UptimeSeconds();
  response->set_status(degraded ? degraded_reason : "ok");
  response->set_service("matching-cpp");
  response->set_version(service_version_);
  response->set_uptime_seconds(uptime);
  response->set_degraded(degraded);
  response->set_degraded_reason(degraded_reason);
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

  response->set_live_orders(static_cast<std::uint64_t>(stats.live_orders));
  response->set_trade_count(static_cast<std::uint64_t>(stats.trade_count));
  response->set_tracked_orders(static_cast<std::uint64_t>(stats.tracked_orders));
  response->set_rejected_orders(static_cast<std::uint64_t>(stats.rejected_orders));
  response->set_symbols(static_cast<std::uint64_t>(stats.symbols));

  if (stats.best_bid.has_value()) {
    response->set_has_best_bid(true);
    response->set_best_bid(*stats.best_bid);
  } else {
    response->set_has_best_bid(false);
  }
  if (stats.best_ask.has_value()) {
    response->set_has_best_ask(true);
    response->set_best_ask(*stats.best_ask);
  } else {
    response->set_has_best_ask(false);
  }
  response->set_submit_order_requests_total(submit_order_requests_total_.load());
  response->set_submit_order_errors_total(submit_order_errors_total_.load());
  response->set_submit_order_rejections_total(submit_order_rejections_total_.load());
  response->set_submit_order_latency_p95_ms(SubmitOrderLatencyP95Ms());
  response->set_submit_order_throughput_rps(SubmitOrderThroughputRps());
  response->set_degraded(degraded);
  response->set_degraded_reason(degraded_reason);
  response->set_inflight_requests(inflight_requests_.load());
  response->set_inflight_requests_peak(inflight_requests_peak_.load());
  response->set_max_inflight_requests(static_cast<std::uint64_t>(max_inflight_requests_));
  response->set_backpressure_waits_total(backpressure_waits_total_.load());
  response->set_backpressure_rejections_total(backpressure_rejections_total_.load());
  response->set_backpressure_wait_timeouts_total(backpressure_wait_timeouts_total_.load());
  response->set_backpressure_wait_ms_total(backpressure_wait_ms_total_.load());
  response->set_execution_stream_limit(static_cast<std::uint64_t>(execution_stream_limit_));
  response->set_submit_latency_window_size(static_cast<std::uint64_t>(submit_latency_window_size_));
  response->set_grpc_min_pollers(static_cast<std::uint64_t>(std::max(grpc_min_pollers_, 1)));
  response->set_grpc_max_pollers(static_cast<std::uint64_t>(std::max(grpc_max_pollers_, 1)));
  response->set_grpc_num_cqs(static_cast<std::uint64_t>(std::max(grpc_num_cqs_, 1)));
  const auto uptime_seconds = static_cast<double>(UptimeSeconds());
  response->set_trade_throughput_rps(
      uptime_seconds > 0.0 ? static_cast<double>(stats.trade_count) / uptime_seconds : 0.0);

  return grpc::Status::OK;
}
