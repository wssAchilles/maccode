#include <iostream>
#include <iomanip>

#include "order_service.hpp"

int main() {
  std::cout << "Cerberus matching service started (gRPC stub pending integration)." << std::endl;

  OrderService service;
  const auto result = service.Submit(Order{
      .order_id = "boot-1",
      .account_id = "system",
      .symbol = "BTCUSDT",
      .side = Side::Buy,
      .price = 100.0,
      .quantity = 1.0,
      .sequence = 1,
  });

  std::cout << "Warmup order accepted: " << (result.accepted ? "true" : "false") << std::endl;
  std::cout << "Remaining quantity: " << std::fixed << std::setprecision(4) << result.remaining_quantity
            << std::endl;

  auto snapshot = service.Snapshot(5);
  auto stats = service.Stats();
  std::cout << "Book snapshot bids=" << snapshot.bids.size() << " asks=" << snapshot.asks.size()
            << std::endl;
  std::cout << "Service stats live_orders=" << stats.live_orders
            << " trades=" << stats.trade_count
            << " tracked_orders=" << stats.tracked_orders
            << " symbols=" << stats.symbols
            << " rejected_orders=" << stats.rejected_orders << std::endl;

  auto warmup_state = service.GetOrder("boot-1");
  if (warmup_state.has_value()) {
    std::cout << "Warmup order status filled=" << std::fixed << std::setprecision(4)
              << warmup_state->filled_quantity << "/" << warmup_state->quantity << std::endl;
  }
  return 0;
}
