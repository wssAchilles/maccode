#include "order_service.hpp"

#include <algorithm>

std::optional<OrderView> OrderService::GetOrder(const std::string& order_id) const {
  const auto it = orders_.find(order_id);
  if (it == orders_.end()) {
    return std::nullopt;
  }
  return ToOrderView(it->second);
}

OrderBookSnapshot OrderService::Snapshot(std::size_t depth) const {
  if (engines_.empty()) {
    return {};
  }
  return engines_.begin()->second.Snapshot(depth);
}

OrderBookSnapshot OrderService::SnapshotForSymbol(const std::string& symbol, std::size_t depth) const {
  const auto it = engines_.find(symbol);
  if (it == engines_.end()) {
    return {};
  }
  return it->second.Snapshot(depth);
}

std::vector<ExecutionEvent> OrderService::RecentExecutions(std::size_t limit) const {
  if (limit == 0 || executions_.empty()) {
    return {};
  }
  if (limit > executions_.size()) {
    limit = executions_.size();
  }

  std::vector<ExecutionEvent> out;
  out.reserve(limit);
  for (auto it = executions_.rbegin(); it != executions_.rend() && out.size() < limit; ++it) {
    out.push_back(*it);
  }
  return out;
}

std::vector<ExecutionEvent> OrderService::RecentExecutionsForAccount(const std::string& account_id,
                                                                     std::size_t limit) const {
  if (account_id.empty() || limit == 0 || executions_.empty()) {
    return {};
  }

  std::vector<ExecutionEvent> out;
  out.reserve(limit);
  for (auto it = executions_.rbegin(); it != executions_.rend() && out.size() < limit; ++it) {
    if (it->trade.maker_account_id == account_id || it->trade.taker_account_id == account_id) {
      out.push_back(*it);
    }
  }
  return out;
}

ServiceStats OrderService::Stats() const {
  const auto rejected = std::count_if(orders_.begin(), orders_.end(), [](const auto& item) {
    return item.second.status == OrderStatus::Rejected;
  });

  std::size_t live_orders = 0;
  std::size_t trade_count = 0;
  for (const auto& [_, engine] : engines_) {
    live_orders += engine.LiveOrderCount();
    trade_count += engine.TradeCount();
  }

  std::optional<double> best_bid;
  std::optional<double> best_ask;
  if (engines_.size() == 1) {
    const auto& engine = engines_.begin()->second;
    best_bid = engine.BestBid();
    best_ask = engine.BestAsk();
  }

  return ServiceStats{
      .live_orders = live_orders,
      .trade_count = trade_count,
      .tracked_orders = orders_.size(),
      .rejected_orders = static_cast<std::size_t>(rejected),
      .symbols = engines_.size(),
      .best_bid = best_bid,
      .best_ask = best_ask,
  };
}
