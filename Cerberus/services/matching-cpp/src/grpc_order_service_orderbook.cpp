#include "grpc_order_service.hpp"
#include "grpc_order_service_mapping.hpp"

#include <algorithm>
#include <chrono>

#include "grpc_request_logging.hpp"

grpc::Status GrpcOrderService::GetOrderBook(
    grpc::ServerContext* context, const cerberus::order::v1::GetOrderBookRequest* request,
    cerberus::order::v1::GetOrderBookResponse* response) {
  LogRequestStart("GetOrderBook", context);
  EchoRequestId(context);
  if (request->symbol().empty()) {
    return grpc::Status(grpc::StatusCode::INVALID_ARGUMENT, "symbol is required");
  }
  FillResponseContext(context, request->schema_version(), request->correlation_id(),
                      response->mutable_schema_version(), response->mutable_correlation_id());

  const std::string symbol = request->symbol();
  const std::size_t depth =
      request->depth() == 0 ? static_cast<std::size_t>(20) : static_cast<std::size_t>(request->depth());
  response->set_symbol(symbol);
  const auto now = std::chrono::system_clock::now().time_since_epoch();
  const auto millis = std::chrono::duration_cast<std::chrono::milliseconds>(now).count();
  response->set_generated_at_ms(static_cast<std::uint64_t>(std::max<std::int64_t>(millis, 0)));

  if (IsDegraded()) {
    return BuildDegradedUnavailable(context, "GetOrderBook");
  }

  std::optional<InflightPermit> permit;
  if (grpc::Status status = AcquireInflightPermit(context, "GetOrderBook", &permit); !status.ok()) {
    return status;
  }

  std::optional<SymbolOrderBookView> view;
  {
    std::scoped_lock<std::mutex> lock(mu_);
    view = service_.ViewForSymbol(symbol, depth);
  }
  if (view.has_value()) {
    PopulateOrderBookResponse(*view, static_cast<std::uint64_t>(std::max<std::int64_t>(millis, 0)),
                              response);
  } else {
    response->set_symbol(symbol);
    response->set_generated_at_ms(static_cast<std::uint64_t>(std::max<std::int64_t>(millis, 0)));
  }
  if (!view.has_value() || (view->order_book.bids.empty() && view->order_book.asks.empty())) {
    MarkDegraded(context, "degraded:orderbook_empty");
  }

  return grpc::Status::OK;
}
