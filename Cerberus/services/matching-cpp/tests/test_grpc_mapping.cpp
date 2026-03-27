#include <cstdlib>
#include <iostream>

#include "grpc_order_service_mapping.hpp"

namespace {

int Fail(const char* message) {
  std::cerr << message << std::endl;
  return 1;
}

}  // namespace

int main() {
  {
    SymbolOrderBookView view{
        .symbol = "BTCUSDT",
        .stats = MatchingEngineStats{},
        .order_book =
            OrderBookSnapshot{
                .bids = {{100.0, 1.5, 2}},
                .asks = {{100.5, 0.8, 1}},
            },
    };
    cerberus::order::v1::GetOrderBookResponse response;
    PopulateOrderBookResponse(view, 1700000000000ULL, &response);
    if (response.symbol() != "BTCUSDT") {
      return Fail("orderbook symbol mismatch");
    }
    if (response.generated_at_ms() != 1700000000000ULL) {
      return Fail("orderbook generated_at_ms mismatch");
    }
    if (response.bids_size() != 1 || response.asks_size() != 1) {
      return Fail("orderbook level count mismatch");
    }
    if (response.bids(0).price() != 100.0 || response.asks(0).price() != 100.5) {
      return Fail("orderbook level values mismatch");
    }
  }

  {
    cerberus::order::v1::HealthResponse response;
    PopulateHealthResponse(true, "manual override", "0.2.0", 42, &response);
    if (response.status() != "manual override" || response.service() != "matching-cpp" ||
        response.version() != "0.2.0" || response.uptime_seconds() != 42ULL ||
        !response.degraded() || response.degraded_reason() != "manual override") {
      return Fail("health response mismatch");
    }
  }

  {
    cerberus::order::v1::GetServiceStatsResponse response;
    PopulateServiceStatsResponse(
        ServiceStats{
            .live_orders = 3,
            .trade_count = 9,
            .tracked_orders = 12,
            .rejected_orders = 1,
            .symbols = 2,
            .best_bid = 99.5,
            .best_ask = 100.2,
        },
        GrpcServiceRuntimeStats{
            .submit_order_requests_total = 11,
            .submit_order_errors_total = 2,
            .submit_order_rejections_total = 1,
            .submit_order_latency_p95_ms = 17.5,
            .submit_order_throughput_rps = 8.0,
            .inflight_requests = 4,
            .inflight_requests_peak = 7,
            .max_inflight_requests = 128,
            .backpressure_waits_total = 6,
            .backpressure_rejections_total = 1,
            .backpressure_wait_timeouts_total = 0,
            .backpressure_wait_ms_total = 13,
            .execution_stream_limit = 500,
            .submit_latency_window_size = 1024,
            .grpc_min_pollers = 4,
            .grpc_max_pollers = 8,
            .grpc_num_cqs = 4,
        },
        false, "", 3.0, &response);
    if (response.live_orders() != 3ULL || response.trade_count() != 9ULL ||
        response.tracked_orders() != 12ULL || !response.has_best_bid() ||
        response.best_bid() != 99.5 || !response.has_best_ask() || response.best_ask() != 100.2 ||
        response.submit_order_requests_total() != 11ULL ||
        response.submit_order_latency_p95_ms() != 17.5 ||
        response.submit_order_throughput_rps() != 8.0 ||
        response.trade_throughput_rps() != 3.0 || response.grpc_num_cqs() != 4ULL) {
      return Fail("service stats response mismatch");
    }
  }

  return 0;
}
