#include "matching_engine.hpp"

namespace {

template <typename BookType>
std::vector<PriceLevelAggregate> BuildSnapshot(const BookType& book, std::size_t depth) {
  std::vector<PriceLevelAggregate> out;
  out.reserve(depth);

  for (const auto& [price, queue] : book) {
    if (out.size() >= depth) {
      break;
    }

    double total = 0.0;
    for (const auto& order : queue) {
      total += order.quantity;
    }

    out.push_back(PriceLevelAggregate{
        .price = price,
        .total_quantity = total,
        .order_count = queue.size(),
    });
  }

  return out;
}

}  // namespace

std::optional<double> MatchingEngine::BestBid() const {
  if (bids_.empty()) {
    return std::nullopt;
  }
  return bids_.begin()->first;
}

std::optional<double> MatchingEngine::BestAsk() const {
  if (asks_.empty()) {
    return std::nullopt;
  }
  return asks_.begin()->first;
}

OrderBookSnapshot MatchingEngine::Snapshot(std::size_t depth) const {
  return OrderBookSnapshot{
      .bids = BuildSnapshot(bids_, depth),
      .asks = BuildSnapshot(asks_, depth),
  };
}

MatchingEngineStats MatchingEngine::Stats() const {
  return MatchingEngineStats{
      .live_orders = LiveOrderCount(),
      .trade_count = TradeCount(),
      .best_bid = BestBid(),
      .best_ask = BestAsk(),
  };
}

MatchingEngineView MatchingEngine::View(std::size_t depth) const {
  return MatchingEngineView{
      .stats = Stats(),
      .order_book = Snapshot(depth),
  };
}

std::size_t MatchingEngine::LiveOrderCount() const {
  return live_order_ids_.size();
}

std::size_t MatchingEngine::TradeCount() const {
  return trade_count_;
}
