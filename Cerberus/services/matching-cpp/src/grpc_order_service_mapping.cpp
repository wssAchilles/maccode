#include "grpc_order_service_mapping.hpp"

void PopulateOrderBookResponse(const SymbolOrderBookView& view, std::uint64_t generated_at_ms,
                               cerberus::order::v1::GetOrderBookResponse* response) {
  response->set_symbol(view.symbol);
  response->set_generated_at_ms(generated_at_ms);
  for (const auto& level : view.order_book.bids) {
    auto* out = response->add_bids();
    out->set_price(level.price);
    out->set_total_quantity(level.total_quantity);
    out->set_order_count(static_cast<std::uint64_t>(level.order_count));
  }
  for (const auto& level : view.order_book.asks) {
    auto* out = response->add_asks();
    out->set_price(level.price);
    out->set_total_quantity(level.total_quantity);
    out->set_order_count(static_cast<std::uint64_t>(level.order_count));
  }
}

void PopulateHealthResponse(bool degraded, const std::string& degraded_reason,
                            const std::string& service_version, std::uint64_t uptime_seconds,
                            cerberus::order::v1::HealthResponse* response) {
  response->set_status(degraded ? degraded_reason : "ok");
  response->set_service("matching-cpp");
  response->set_version(service_version);
  response->set_uptime_seconds(uptime_seconds);
  response->set_degraded(degraded);
  response->set_degraded_reason(degraded_reason);
}

void PopulateServiceStatsResponse(const ServiceStats& stats,
                                  const GrpcServiceRuntimeStats& runtime_stats, bool degraded,
                                  const std::string& degraded_reason, double uptime_seconds,
                                  cerberus::order::v1::GetServiceStatsResponse* response) {
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

  response->set_submit_order_requests_total(runtime_stats.submit_order_requests_total);
  response->set_submit_order_errors_total(runtime_stats.submit_order_errors_total);
  response->set_submit_order_rejections_total(runtime_stats.submit_order_rejections_total);
  response->set_submit_order_latency_p95_ms(runtime_stats.submit_order_latency_p95_ms);
  response->set_submit_order_throughput_rps(runtime_stats.submit_order_throughput_rps);
  response->set_trade_throughput_rps(
      uptime_seconds > 0.0 ? static_cast<double>(stats.trade_count) / uptime_seconds : 0.0);
  response->set_degraded(degraded);
  response->set_degraded_reason(degraded_reason);
  response->set_inflight_requests(runtime_stats.inflight_requests);
  response->set_inflight_requests_peak(runtime_stats.inflight_requests_peak);
  response->set_max_inflight_requests(runtime_stats.max_inflight_requests);
  response->set_backpressure_waits_total(runtime_stats.backpressure_waits_total);
  response->set_backpressure_rejections_total(runtime_stats.backpressure_rejections_total);
  response->set_backpressure_wait_timeouts_total(runtime_stats.backpressure_wait_timeouts_total);
  response->set_backpressure_wait_ms_total(runtime_stats.backpressure_wait_ms_total);
  response->set_execution_stream_limit(runtime_stats.execution_stream_limit);
  response->set_submit_latency_window_size(runtime_stats.submit_latency_window_size);
  response->set_grpc_min_pollers(runtime_stats.grpc_min_pollers);
  response->set_grpc_max_pollers(runtime_stats.grpc_max_pollers);
  response->set_grpc_num_cqs(runtime_stats.grpc_num_cqs);
}
