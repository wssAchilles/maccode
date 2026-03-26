#include <cstdlib>
#include <iostream>
#include <iomanip>
#include <string>

#include "order_service.hpp"

namespace {

bool ReadEnvBool(const char* key, bool default_value) {
  const char* raw = std::getenv(key);
  if (raw == nullptr || *raw == '\0') {
    return default_value;
  }
  const std::string value(raw);
  return value == "1" || value == "true" || value == "TRUE" || value == "yes" || value == "on";
}

int RunWarmupOrderbookProbe() {
  std::cout << "Cerberus matching warmup probe started (non-gRPC fallback mode)." << std::endl;

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

}  // namespace

int main() {
  if (!ReadEnvBool("MATCHING_ALLOW_STUB_STARTUP", false)) {
    std::cerr << "non-gRPC matching binary is disabled by default. "
              << "set MATCHING_ALLOW_STUB_STARTUP=true for diagnostic startup only." << std::endl;
    return 78;
  }
  return RunWarmupOrderbookProbe();
}
