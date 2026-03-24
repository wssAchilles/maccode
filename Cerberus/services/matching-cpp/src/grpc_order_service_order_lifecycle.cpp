#include "grpc_order_service.hpp"

#include "grpc_request_logging.hpp"

grpc::Status GrpcOrderService::CancelOrder(
    grpc::ServerContext* context,
    const cerberus::order::v1::CancelOrderRequest* request,
    cerberus::order::v1::CancelOrderResponse* response) {
  LogRequestStart("CancelOrder", context);
  if (request->order_id().empty()) {
    return grpc::Status(grpc::StatusCode::INVALID_ARGUMENT, "order_id is required");
  }

  {
    std::scoped_lock<std::mutex> lock(mu_);
    const auto order = service_.GetOrder(request->order_id());
    if (!order.has_value()) {
      response->set_canceled(false);
      response->set_reason("order not found");
      return grpc::Status::OK;
    }

    if (!request->account_id().empty() && order->account_id != request->account_id()) {
      response->set_canceled(false);
      response->set_reason("account mismatch");
      return grpc::Status::OK;
    }

    const bool canceled = service_.Cancel(request->order_id());
    response->set_canceled(canceled);
    response->set_reason(canceled ? "" : "order is not cancelable");
  }

  return grpc::Status::OK;
}

grpc::Status GrpcOrderService::GetOrder(grpc::ServerContext* context,
                                        const cerberus::order::v1::GetOrderRequest* request,
                                        cerberus::order::v1::GetOrderResponse* response) {
  LogRequestStart("GetOrder", context);
  if (request->order_id().empty()) {
    return grpc::Status(grpc::StatusCode::INVALID_ARGUMENT, "order_id is required");
  }

  std::optional<OrderView> order;
  {
    std::scoped_lock<std::mutex> lock(mu_);
    order = service_.GetOrder(request->order_id());
  }

  if (!order.has_value()) {
    return grpc::Status(grpc::StatusCode::NOT_FOUND, "order not found");
  }
  if (!request->account_id().empty() && order->account_id != request->account_id()) {
    return grpc::Status(grpc::StatusCode::PERMISSION_DENIED, "account mismatch");
  }

  response->set_order_id(order->order_id);
  response->set_account_id(order->account_id);
  response->set_symbol(order->symbol);
  response->set_side(ToProtoSide(order->side));
  response->set_order_type(cerberus::order::v1::ORDER_TYPE_LIMIT);
  response->set_price(order->price);
  response->set_quantity(order->quantity);
  response->set_filled_quantity(order->filled_quantity);
  response->set_status(ToProtoStatus(order->status));
  FillNowTimestamp(response->mutable_updated_at());
  return grpc::Status::OK;
}
