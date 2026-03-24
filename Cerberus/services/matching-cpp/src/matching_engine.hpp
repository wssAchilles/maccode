#pragma once

#include <cstdint>
#include <deque>
#include <map>
#include <optional>
#include <string>
#include <unordered_set>
#include <vector>

enum class Side {
  Buy,
  Sell,
};

struct Order {
  std::string order_id;
  std::string account_id;
  std::string symbol;
  Side side;
  double price;
  double quantity;
  std::uint64_t sequence;
};

struct Trade {
  std::string maker_order_id;
  std::string maker_account_id;
  std::string taker_order_id;
  std::string taker_account_id;
  std::string symbol;
  double price;
  double quantity;
};

struct SubmitResult {
  bool accepted;
  std::vector<Trade> trades;
  double remaining_quantity;
  std::string reason;
};

struct PriceLevelAggregate {
  double price;
  double total_quantity;
  std::size_t order_count;
};

struct OrderBookSnapshot {
  std::vector<PriceLevelAggregate> bids;
  std::vector<PriceLevelAggregate> asks;
};

class MatchingEngine {
 public:
  SubmitResult Submit(const Order& order);
  bool Cancel(const std::string& order_id);
  std::optional<Order> Find(const std::string& order_id) const;
  std::optional<double> BestBid() const;
  std::optional<double> BestAsk() const;
  OrderBookSnapshot Snapshot(std::size_t depth = 20) const;
  std::size_t LiveOrderCount() const;
  std::size_t TradeCount() const;

 private:
  using PriceLevel = std::deque<Order>;
  std::map<double, PriceLevel, std::greater<>> bids_;
  std::map<double, PriceLevel, std::less<>> asks_;
  std::unordered_set<std::string> live_order_ids_;
  std::string symbol_;
  std::uint64_t last_sequence_ = 0;
  std::size_t trade_count_ = 0;

  static bool IsValid(const Order& order);
};
