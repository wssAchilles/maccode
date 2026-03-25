#include "grpc_order_service.hpp"

#include <algorithm>
#include <chrono>

#include "grpc_request_logging.hpp"

grpc::Status GrpcOrderService::Health(grpc::ServerContext* context,
                                      const cerberus::order::v1::HealthRequest* /*request*/,
                                      cerberus::order::v1::HealthResponse* response) {
  LogRequestStart("Health", context);
  EchoRequestId(context);
  const auto uptime =
      std::chrono::duration_cast<std::chrono::seconds>(std::chrono::steady_clock::now() - started_at_)
          .count();
  response->set_status("ok");
  response->set_service("matching-cpp");
  response->set_version(service_version_);
  response->set_uptime_seconds(static_cast<std::uint64_t>(std::max<std::int64_t>(uptime, 0)));
  return grpc::Status::OK;
}

grpc::Status GrpcOrderService::GetServiceStats(
    grpc::ServerContext* context, const cerberus::order::v1::GetServiceStatsRequest* /*request*/,
    cerberus::order::v1::GetServiceStatsResponse* response) {
  LogRequestStart("GetServiceStats", context);
  EchoRequestId(context);
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

  return grpc::Status::OK;
}
