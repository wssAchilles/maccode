#include "grpc_order_service.hpp"

#include "grpc_request_logging.hpp"

grpc::Status GrpcOrderService::SubmitOrder(grpc::ServerContext* context,
                                           const cerberus::order::v1::SubmitOrderRequest* request,
                                           cerberus::order::v1::SubmitOrderResponse* response) {
  LogRequestStart("SubmitOrder", context);
  EchoRequestId(context);
  if (request->account_id().empty()) {
    return grpc::Status(grpc::StatusCode::INVALID_ARGUMENT, "account_id is required");
  }
  if (request->symbol().empty()) {
    return grpc::Status(grpc::StatusCode::INVALID_ARGUMENT, "symbol is required");
  }
  if (request->quantity() <= 0.0) {
    return grpc::Status(grpc::StatusCode::INVALID_ARGUMENT, "quantity must be > 0");
  }
  if (request->order_type() == cerberus::order::v1::ORDER_TYPE_MARKET) {
    response->set_accepted(false);
    response->set_reason("market order not implemented");
    return grpc::Status::OK;
  }

  bool side_ok = false;
  const Side side = ToDomainSide(request->side(), side_ok);
  if (!side_ok) {
    return grpc::Status(grpc::StatusCode::INVALID_ARGUMENT, "side must be SIDE_BUY or SIDE_SELL");
  }

  const std::string order_id = request->client_order_id().empty()
                                   ? NextGeneratedOrderId(request->account_id())
                                   : request->client_order_id();

  const Order order{
      .order_id = order_id,
      .account_id = request->account_id(),
      .symbol = request->symbol(),
      .side = side,
      .price = request->price(),
      .quantity = request->quantity(),
      .sequence = next_sequence_.fetch_add(1),
  };

  SubmitResult result;
  {
    std::scoped_lock<std::mutex> lock(mu_);
    result = service_.Submit(order);
  }

  response->set_accepted(result.accepted);
  response->set_order_id(order.order_id);
  response->set_reason(result.reason);
  return grpc::Status::OK;
}
