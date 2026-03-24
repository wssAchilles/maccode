#include "matching_engine.hpp"

#include <algorithm>
#include <cmath>

namespace {

constexpr double kQuantityEpsilon = 1e-12;

}  // namespace

bool MatchingEngine::IsValid(const Order& order) {
  return !order.order_id.empty() && !order.account_id.empty() && !order.symbol.empty() &&
         order.price > 0.0 && order.quantity > 0.0 && order.sequence > 0 &&
         std::isfinite(order.price) && std::isfinite(order.quantity);
}

SubmitResult MatchingEngine::Submit(const Order& input) {
  if (!IsValid(input)) {
    return {.accepted = false, .trades = {}, .remaining_quantity = input.quantity, .reason = "invalid order"};
  }
  if (!symbol_.empty() && input.symbol != symbol_) {
    return {.accepted = false,
            .trades = {},
            .remaining_quantity = input.quantity,
            .reason = "symbol mismatch"};
  }
  if (last_sequence_ != 0 && input.sequence <= last_sequence_) {
    return {.accepted = false,
            .trades = {},
            .remaining_quantity = input.quantity,
            .reason = "non-monotonic sequence"};
  }
  if (live_order_ids_.contains(input.order_id)) {
    return {.accepted = false,
            .trades = {},
            .remaining_quantity = input.quantity,
            .reason = "duplicate order_id"};
  }

  if (symbol_.empty()) {
    symbol_ = input.symbol;
  }
  last_sequence_ = input.sequence;

  Order incoming = input;
  std::vector<Trade> trades;

  if (incoming.side == Side::Buy) {
    while (incoming.quantity > kQuantityEpsilon && !asks_.empty()) {
      auto best_ask_it = asks_.begin();
      if (best_ask_it->first > incoming.price) {
        break;
      }

      auto& queue = best_ask_it->second;
      while (incoming.quantity > kQuantityEpsilon && !queue.empty()) {
        auto& maker = queue.front();
        const double matched = std::min(incoming.quantity, maker.quantity);
        incoming.quantity -= matched;
        maker.quantity -= matched;

        trades.push_back(Trade{
            .maker_order_id = maker.order_id,
            .maker_account_id = maker.account_id,
            .taker_order_id = incoming.order_id,
            .taker_account_id = incoming.account_id,
            .symbol = incoming.symbol,
            .price = maker.price,
            .quantity = matched,
        });

        if (maker.quantity <= kQuantityEpsilon) {
          live_order_ids_.erase(maker.order_id);
          queue.pop_front();
        }
      }

      if (queue.empty()) {
        asks_.erase(best_ask_it);
      }
    }

    if (incoming.quantity > kQuantityEpsilon) {
      bids_[incoming.price].push_back(incoming);
      live_order_ids_.insert(incoming.order_id);
    }
  } else {
    while (incoming.quantity > kQuantityEpsilon && !bids_.empty()) {
      auto best_bid_it = bids_.begin();
      if (best_bid_it->first < incoming.price) {
        break;
      }

      auto& queue = best_bid_it->second;
      while (incoming.quantity > kQuantityEpsilon && !queue.empty()) {
        auto& maker = queue.front();
        const double matched = std::min(incoming.quantity, maker.quantity);
        incoming.quantity -= matched;
        maker.quantity -= matched;

        trades.push_back(Trade{
            .maker_order_id = maker.order_id,
            .maker_account_id = maker.account_id,
            .taker_order_id = incoming.order_id,
            .taker_account_id = incoming.account_id,
            .symbol = incoming.symbol,
            .price = maker.price,
            .quantity = matched,
        });

        if (maker.quantity <= kQuantityEpsilon) {
          live_order_ids_.erase(maker.order_id);
          queue.pop_front();
        }
      }

      if (queue.empty()) {
        bids_.erase(best_bid_it);
      }
    }

    if (incoming.quantity > kQuantityEpsilon) {
      asks_[incoming.price].push_back(incoming);
      live_order_ids_.insert(incoming.order_id);
    }
  }

  if (incoming.quantity <= kQuantityEpsilon) {
    incoming.quantity = 0.0;
  }

  trade_count_ += trades.size();
  return {.accepted = true, .trades = std::move(trades), .remaining_quantity = incoming.quantity, .reason = ""};
}
