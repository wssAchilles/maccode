#include "grpc_order_service.hpp"

#include <algorithm>
#include <vector>

#include "grpc_request_logging.hpp"

namespace {

constexpr std::size_t kExecutionStreamLimit = 500;

}  // namespace

grpc::Status GrpcOrderService::StreamExecutions(
    grpc::ServerContext* context,
    const cerberus::order::v1::StreamExecutionsRequest* request,
    grpc::ServerWriter<cerberus::order::v1::StreamExecutionsResponse>* writer) {
  LogRequestStart("StreamExecutions", context);
  if (request->account_id().empty()) {
    return grpc::Status(grpc::StatusCode::INVALID_ARGUMENT, "account_id is required");
  }

  std::vector<ExecutionEvent> executions;
  {
    std::scoped_lock<std::mutex> lock(mu_);
    executions = service_.RecentExecutionsForAccount(request->account_id(), kExecutionStreamLimit);
  }

  std::reverse(executions.begin(), executions.end());
  for (const auto& execution : executions) {
    cerberus::order::v1::StreamExecutionsResponse message;
    message.set_execution_id(std::to_string(execution.event_id));
    if (execution.trade.taker_account_id == request->account_id()) {
      message.set_order_id(execution.trade.taker_order_id);
    } else {
      message.set_order_id(execution.trade.maker_order_id);
    }
    message.set_symbol(execution.trade.symbol);
    message.set_price(execution.trade.price);
    message.set_quantity(execution.trade.quantity);
    FillNowTimestamp(message.mutable_event_time());

    if (!writer->Write(message)) {
      break;
    }
  }

  return grpc::Status::OK;
}
