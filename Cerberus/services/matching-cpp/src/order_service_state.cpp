#include "order_service.hpp"

OrderView OrderService::ToOrderView(const MutableOrderState& state) {
  return OrderView{
      .order_id = state.base.order_id,
      .account_id = state.base.account_id,
      .symbol = state.base.symbol,
      .side = state.base.side,
      .price = state.base.price,
      .quantity = state.base.quantity,
      .filled_quantity = state.filled_quantity,
      .status = state.status,
      .reason = state.reason,
      .last_sequence = state.last_sequence,
  };
}

void OrderService::UpsertAcceptedOrder(const Order& order, double remaining_quantity) {
  if (remaining_quantity <= kQtyEpsilon) {
    remaining_quantity = 0.0;
  }

  double filled = order.quantity - remaining_quantity;
  if (filled <= kQtyEpsilon) {
    filled = 0.0;
  }

  OrderStatus status = OrderStatus::New;
  if (remaining_quantity == 0.0) {
    status = OrderStatus::Filled;
  } else if (filled > 0.0) {
    status = OrderStatus::PartiallyFilled;
  }

  orders_[order.order_id] = MutableOrderState{
      .base = order,
      .remaining_quantity = remaining_quantity,
      .filled_quantity = filled,
      .status = status,
      .reason = "",
      .last_sequence = order.sequence,
  };
}

void OrderService::ApplyMakerFill(const Trade& trade) {
  const auto it = orders_.find(trade.maker_order_id);
  if (it == orders_.end()) {
    return;
  }

  auto& state = it->second;
  state.filled_quantity += trade.quantity;
  if (state.filled_quantity >= state.base.quantity - kQtyEpsilon) {
    state.filled_quantity = state.base.quantity;
    state.remaining_quantity = 0.0;
    state.status = OrderStatus::Filled;
  } else {
    state.remaining_quantity = state.base.quantity - state.filled_quantity;
    state.status = OrderStatus::PartiallyFilled;
  }
  state.reason.clear();
}

void OrderService::MarkRejectedIfAbsent(const Order& order, const std::string& reason) {
  if (orders_.contains(order.order_id)) {
    return;
  }

  orders_.emplace(order.order_id,
                  MutableOrderState{
                      .base = order,
                      .remaining_quantity = order.quantity,
                      .filled_quantity = 0.0,
                      .status = OrderStatus::Rejected,
                      .reason = reason,
                      .last_sequence = order.sequence,
                  });
}

void OrderService::MarkCanceled(const std::string& order_id) {
  const auto it = orders_.find(order_id);
  if (it == orders_.end()) {
    return;
  }

  auto& state = it->second;
  state.status = OrderStatus::Canceled;
  state.reason.clear();
}
