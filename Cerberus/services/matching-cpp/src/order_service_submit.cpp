#include "order_service.hpp"

SubmitResult OrderService::Submit(const Order& order) {
  auto& engine = engines_[order.symbol];
  auto result = engine.Submit(order);
  if (!result.accepted) {
    MarkRejectedIfAbsent(order, result.reason);
    return result;
  }

  UpsertAcceptedOrder(order, result.remaining_quantity);

  for (const auto& trade : result.trades) {
    executions_.push_back(ExecutionEvent{
        .event_id = next_execution_id_++,
        .trade = trade,
    });
    ApplyMakerFill(trade);
  }

  return result;
}

bool OrderService::Cancel(const std::string& order_id) {
  const auto order_it = orders_.find(order_id);
  if (order_it == orders_.end()) {
    return false;
  }
  const auto engine_it = engines_.find(order_it->second.base.symbol);
  if (engine_it == engines_.end()) {
    return false;
  }

  const bool canceled = engine_it->second.Cancel(order_id);
  if (canceled) {
    MarkCanceled(order_id);
  }
  return canceled;
}
