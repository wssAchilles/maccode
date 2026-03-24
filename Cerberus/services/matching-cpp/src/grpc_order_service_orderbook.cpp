#include "grpc_order_service.hpp"

#include <algorithm>
#include <chrono>

#include "grpc_request_logging.hpp"

grpc::Status GrpcOrderService::GetOrderBook(
    grpc::ServerContext* context, const cerberus::order::v1::GetOrderBookRequest* request,
    cerberus::order::v1::GetOrderBookResponse* response) {
  LogRequestStart("GetOrderBook", context);
  if (request->symbol().empty()) {
    return grpc::Status(grpc::StatusCode::INVALID_ARGUMENT, "symbol is required");
  }

  const std::string symbol = request->symbol();
  const std::size_t depth =
      request->depth() == 0 ? static_cast<std::size_t>(20) : static_cast<std::size_t>(request->depth());
  OrderBookSnapshot snapshot;
  {
    std::scoped_lock<std::mutex> lock(mu_);
    snapshot = service_.SnapshotForSymbol(symbol, depth);
  }

  response->set_symbol(symbol);
  const auto now = std::chrono::system_clock::now().time_since_epoch();
  const auto millis = std::chrono::duration_cast<std::chrono::milliseconds>(now).count();
  response->set_generated_at_ms(static_cast<std::uint64_t>(std::max<std::int64_t>(millis, 0)));

  for (const auto& level : snapshot.bids) {
    auto* out = response->add_bids();
    out->set_price(level.price);
    out->set_total_quantity(level.total_quantity);
    out->set_order_count(static_cast<std::uint64_t>(level.order_count));
  }
  for (const auto& level : snapshot.asks) {
    auto* out = response->add_asks();
    out->set_price(level.price);
    out->set_total_quantity(level.total_quantity);
    out->set_order_count(static_cast<std::uint64_t>(level.order_count));
  }

  return grpc::Status::OK;
}
