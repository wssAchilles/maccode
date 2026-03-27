#pragma once

#include <cstddef>
#include <cstdint>
#include <cmath>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

#include "matching_engine.hpp"

struct ExecutionEvent {
  std::uint64_t event_id;
  std::uint64_t event_time_ms;
  Trade trade;
};

enum class OrderStatus {
  New,
  PartiallyFilled,
  Filled,
  Canceled,
  Rejected,
};

struct OrderView {
  std::string order_id;
  std::string account_id;
  std::string symbol;
  Side side;
  double price;
  double quantity;
  double filled_quantity;
  OrderStatus status;
  std::string reason;
  std::uint64_t last_sequence;
};

struct ServiceStats {
  std::size_t live_orders;
  std::size_t trade_count;
  std::size_t tracked_orders;
  std::size_t rejected_orders;
  std::size_t symbols;
  std::optional<double> best_bid;
  std::optional<double> best_ask;
};

struct SymbolOrderBookView {
  std::string symbol;
  MatchingEngineStats stats;
  OrderBookSnapshot order_book;
};

class OrderService {
 public:
  SubmitResult Submit(const Order& order);
  bool Cancel(const std::string& order_id);
  std::optional<OrderView> GetOrder(const std::string& order_id) const;
  OrderBookSnapshot Snapshot(std::size_t depth = 20) const;
  OrderBookSnapshot SnapshotForSymbol(const std::string& symbol, std::size_t depth = 20) const;
  std::optional<SymbolOrderBookView> ViewForSymbol(const std::string& symbol,
                                                   std::size_t depth = 20) const;
  std::vector<ExecutionEvent> RecentExecutions(std::size_t limit = 50) const;
  std::vector<ExecutionEvent> RecentExecutionsForAccount(const std::string& account_id,
                                                         std::size_t limit = 50) const;
  ServiceStats Stats() const;

 private:
  struct MutableOrderState {
    Order base;
    double remaining_quantity;
    double filled_quantity;
    OrderStatus status;
    std::string reason;
    std::uint64_t last_sequence;
  };

  static constexpr double kQtyEpsilon = 1e-12;

  static OrderView ToOrderView(const MutableOrderState& state);
  void UpsertAcceptedOrder(const Order& order, double remaining_quantity);
  void ApplyMakerFill(const Trade& trade);
  void MarkRejectedIfAbsent(const Order& order, const std::string& reason);
  void MarkCanceled(const std::string& order_id);

  std::unordered_map<std::string, MatchingEngine> engines_;
  std::vector<ExecutionEvent> executions_;
  std::unordered_map<std::string, MutableOrderState> orders_;
  std::uint64_t next_execution_id_ = 1;
};
