#include "order_service.hpp"

#include <chrono>

namespace {

std::uint64_t current_epoch_ms() {
  const auto now = std::chrono::system_clock::now().time_since_epoch();
  return static_cast<std::uint64_t>(
      std::chrono::duration_cast<std::chrono::milliseconds>(now).count());
}

}  // namespace

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
        .event_time_ms = current_epoch_ms(),
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
