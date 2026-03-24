#include "matching_engine.hpp"

#include <algorithm>

bool MatchingEngine::Cancel(const std::string& order_id) {
  for (auto it = bids_.begin(); it != bids_.end(); ++it) {
    auto& queue = it->second;
    auto qit = std::find_if(queue.begin(), queue.end(), [&](const Order& o) { return o.order_id == order_id; });
    if (qit != queue.end()) {
      queue.erase(qit);
      live_order_ids_.erase(order_id);
      if (queue.empty()) {
        bids_.erase(it);
      }
      return true;
    }
  }

  for (auto it = asks_.begin(); it != asks_.end(); ++it) {
    auto& queue = it->second;
    auto qit = std::find_if(queue.begin(), queue.end(), [&](const Order& o) { return o.order_id == order_id; });
    if (qit != queue.end()) {
      queue.erase(qit);
      live_order_ids_.erase(order_id);
      if (queue.empty()) {
        asks_.erase(it);
      }
      return true;
    }
  }

  return false;
}

std::optional<Order> MatchingEngine::Find(const std::string& order_id) const {
  for (const auto& [_, queue] : bids_) {
    auto it = std::find_if(queue.begin(), queue.end(), [&](const Order& o) { return o.order_id == order_id; });
    if (it != queue.end()) {
      return *it;
    }
  }

  for (const auto& [_, queue] : asks_) {
    auto it = std::find_if(queue.begin(), queue.end(), [&](const Order& o) { return o.order_id == order_id; });
    if (it != queue.end()) {
      return *it;
    }
  }

  return std::nullopt;
}
