#include "grpc_order_service.hpp"

#include <algorithm>
#include <chrono>
#include <vector>

#include "grpc_request_logging.hpp"

namespace {

void FillTimestampFromMillis(std::uint64_t epoch_ms, google::protobuf::Timestamp* ts) {
  if (ts == nullptr) {
    return;
  }
  const auto millis = std::chrono::milliseconds(epoch_ms);
  const auto seconds = std::chrono::duration_cast<std::chrono::seconds>(millis);
  const auto nanos = std::chrono::duration_cast<std::chrono::nanoseconds>(millis - seconds);
  ts->set_seconds(seconds.count());
  ts->set_nanos(static_cast<int>(nanos.count()));
}

}  // namespace

grpc::Status GrpcOrderService::StreamExecutions(
    grpc::ServerContext* context,
    const cerberus::order::v1::StreamExecutionsRequest* request,
    grpc::ServerWriter<cerberus::order::v1::StreamExecutionsResponse>* writer) {
  LogRequestStart("StreamExecutions", context);
  EchoRequestId(context);
  if (IsDegraded()) {
    MarkDegraded(context, DegradedStatusText());
    return grpc::Status::OK;
  }
  if (request->account_id().empty()) {
    return grpc::Status(grpc::StatusCode::INVALID_ARGUMENT, "account_id is required");
  }

  std::vector<ExecutionEvent> executions;
  {
    std::scoped_lock<std::mutex> lock(mu_);
    executions = service_.RecentExecutionsForAccount(request->account_id(), execution_stream_limit_);
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
    FillTimestampFromMillis(execution.event_time_ms, message.mutable_event_time());
    FillResponseContext(context, request->schema_version(), request->correlation_id(),
                        message.mutable_schema_version(), message.mutable_correlation_id());

    if (!writer->Write(message)) {
      break;
    }
  }

  return grpc::Status::OK;
}
