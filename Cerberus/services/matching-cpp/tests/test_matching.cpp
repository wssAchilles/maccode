#include <gtest/gtest.h>

#include "matching_engine.hpp"
#include "order_service.hpp"

TEST(MatchingEngineTest, MatchesCrossingOrders) {
  MatchingEngine engine;

  auto first = engine.Submit(Order{
      .order_id = "sell-1",
      .account_id = "a1",
      .symbol = "BTCUSDT",
      .side = Side::Sell,
      .price = 100.0,
      .quantity = 1.0,
      .sequence = 1,
  });
  ASSERT_TRUE(first.accepted);
  ASSERT_TRUE(first.trades.empty());
  EXPECT_DOUBLE_EQ(first.remaining_quantity, 1.0);

  auto second = engine.Submit(Order{
      .order_id = "buy-1",
      .account_id = "a2",
      .symbol = "BTCUSDT",
      .side = Side::Buy,
      .price = 101.0,
      .quantity = 1.0,
      .sequence = 2,
  });

  ASSERT_TRUE(second.accepted);
  ASSERT_EQ(second.trades.size(), 1);
  EXPECT_EQ(second.trades[0].maker_order_id, "sell-1");
  EXPECT_EQ(second.trades[0].maker_account_id, "a1");
  EXPECT_EQ(second.trades[0].taker_order_id, "buy-1");
  EXPECT_EQ(second.trades[0].taker_account_id, "a2");
  EXPECT_EQ(second.trades[0].symbol, "BTCUSDT");
  EXPECT_DOUBLE_EQ(second.trades[0].quantity, 1.0);
  EXPECT_DOUBLE_EQ(second.remaining_quantity, 0.0);
  EXPECT_EQ(engine.LiveOrderCount(), 0);
  EXPECT_EQ(engine.TradeCount(), 1);
}

TEST(MatchingEngineTest, CancelsOrder) {
  MatchingEngine engine;

  auto result = engine.Submit(Order{
      .order_id = "buy-2",
      .account_id = "a3",
      .symbol = "BTCUSDT",
      .side = Side::Buy,
      .price = 99.0,
      .quantity = 2.0,
      .sequence = 3,
  });
  ASSERT_TRUE(result.accepted);
  EXPECT_EQ(engine.LiveOrderCount(), 1);

  EXPECT_TRUE(engine.Cancel("buy-2"));
  EXPECT_FALSE(engine.Find("buy-2").has_value());
  EXPECT_EQ(engine.LiveOrderCount(), 0);
}

TEST(MatchingEngineTest, RejectsDuplicateOrderId) {
  MatchingEngine engine;
  auto first = engine.Submit(Order{
      .order_id = "dup-1",
      .account_id = "a1",
      .symbol = "BTCUSDT",
      .side = Side::Buy,
      .price = 99.0,
      .quantity = 1.0,
      .sequence = 1,
  });
  ASSERT_TRUE(first.accepted);

  auto second = engine.Submit(Order{
      .order_id = "dup-1",
      .account_id = "a2",
      .symbol = "BTCUSDT",
      .side = Side::Sell,
      .price = 99.0,
      .quantity = 1.0,
      .sequence = 2,
  });
  ASSERT_FALSE(second.accepted);
  EXPECT_EQ(second.reason, "duplicate order_id");
}

TEST(MatchingEngineTest, RejectsMissingAccountId) {
  MatchingEngine engine;
  auto result = engine.Submit(Order{
      .order_id = "bad-1",
      .account_id = "",
      .symbol = "BTCUSDT",
      .side = Side::Buy,
      .price = 100.0,
      .quantity = 1.0,
      .sequence = 1,
  });
  ASSERT_FALSE(result.accepted);
  EXPECT_EQ(result.reason, "invalid order");
}

TEST(MatchingEngineTest, RespectsPriceTimePriorityAtSamePrice) {
  MatchingEngine engine;
  ASSERT_TRUE(engine.Submit(Order{
                 .order_id = "sell-1",
                 .account_id = "a1",
                 .symbol = "BTCUSDT",
                 .side = Side::Sell,
                 .price = 100.0,
                 .quantity = 1.0,
                 .sequence = 1,
             }).accepted);
  ASSERT_TRUE(engine.Submit(Order{
                 .order_id = "sell-2",
                 .account_id = "a2",
                 .symbol = "BTCUSDT",
                 .side = Side::Sell,
                 .price = 100.0,
                 .quantity = 1.0,
                 .sequence = 2,
             }).accepted);

  auto buy = engine.Submit(Order{
      .order_id = "buy-big",
      .account_id = "a3",
      .symbol = "BTCUSDT",
      .side = Side::Buy,
      .price = 101.0,
      .quantity = 2.0,
      .sequence = 3,
  });

  ASSERT_TRUE(buy.accepted);
  ASSERT_EQ(buy.trades.size(), 2);
  EXPECT_EQ(buy.trades[0].maker_order_id, "sell-1");
  EXPECT_EQ(buy.trades[1].maker_order_id, "sell-2");
}

TEST(MatchingEngineTest, PartialFillUpdatesSnapshot) {
  MatchingEngine engine;
  ASSERT_TRUE(engine.Submit(Order{
                 .order_id = "sell-1",
                 .account_id = "a1",
                 .symbol = "BTCUSDT",
                 .side = Side::Sell,
                 .price = 100.0,
                 .quantity = 2.0,
                 .sequence = 1,
             }).accepted);

  auto buy = engine.Submit(Order{
      .order_id = "buy-1",
      .account_id = "a2",
      .symbol = "BTCUSDT",
      .side = Side::Buy,
      .price = 101.0,
      .quantity = 0.5,
      .sequence = 2,
  });
  ASSERT_TRUE(buy.accepted);
  EXPECT_DOUBLE_EQ(buy.remaining_quantity, 0.0);

  auto rest = engine.Find("sell-1");
  ASSERT_TRUE(rest.has_value());
  EXPECT_DOUBLE_EQ(rest->quantity, 1.5);

  auto snapshot = engine.Snapshot(5);
  ASSERT_EQ(snapshot.asks.size(), 1);
  EXPECT_DOUBLE_EQ(snapshot.asks[0].price, 100.0);
  EXPECT_DOUBLE_EQ(snapshot.asks[0].total_quantity, 1.5);
  EXPECT_EQ(snapshot.asks[0].order_count, 1);
}

TEST(MatchingEngineTest, ViewCombinesStatsAndOrderBook) {
  MatchingEngine engine;
  ASSERT_TRUE(engine.Submit(Order{
                 .order_id = "buy-1",
                 .account_id = "a1",
                 .symbol = "BTCUSDT",
                 .side = Side::Buy,
                 .price = 100.0,
                 .quantity = 2.0,
                 .sequence = 1,
             }).accepted);

  const MatchingEngineView view = engine.View(3);

  ASSERT_EQ(view.order_book.bids.size(), 1);
  EXPECT_EQ(view.stats.live_orders, 1);
  EXPECT_EQ(view.stats.trade_count, 0);
  ASSERT_TRUE(view.stats.best_bid.has_value());
  EXPECT_DOUBLE_EQ(*view.stats.best_bid, 100.0);
  EXPECT_FALSE(view.stats.best_ask.has_value());
  EXPECT_DOUBLE_EQ(view.order_book.bids[0].total_quantity, 2.0);
}

TEST(MatchingEngineTest, RejectsNonMonotonicSequence) {
  MatchingEngine engine;
  ASSERT_TRUE(engine.Submit(Order{
                 .order_id = "buy-1",
                 .account_id = "a1",
                 .symbol = "BTCUSDT",
                 .side = Side::Buy,
                 .price = 100.0,
                 .quantity = 1.0,
                 .sequence = 10,
             }).accepted);

  auto late = engine.Submit(Order{
      .order_id = "buy-2",
      .account_id = "a2",
      .symbol = "BTCUSDT",
      .side = Side::Buy,
      .price = 99.0,
      .quantity = 1.0,
      .sequence = 9,
  });
  ASSERT_FALSE(late.accepted);
  EXPECT_EQ(late.reason, "non-monotonic sequence");
}

TEST(MatchingEngineTest, RejectsSymbolMismatch) {
  MatchingEngine engine;
  ASSERT_TRUE(engine.Submit(Order{
                 .order_id = "buy-1",
                 .account_id = "a1",
                 .symbol = "BTCUSDT",
                 .side = Side::Buy,
                 .price = 100.0,
                 .quantity = 1.0,
                 .sequence = 1,
             }).accepted);

  auto wrong_symbol = engine.Submit(Order{
      .order_id = "sell-eth",
      .account_id = "a2",
      .symbol = "ETHUSDT",
      .side = Side::Sell,
      .price = 100.0,
      .quantity = 1.0,
      .sequence = 2,
  });
  ASSERT_FALSE(wrong_symbol.accepted);
  EXPECT_EQ(wrong_symbol.reason, "symbol mismatch");
}

TEST(OrderServiceTest, TracksRecentExecutionEvents) {
  OrderService service;
  ASSERT_TRUE(service.Submit(Order{
                 .order_id = "sell-1",
                 .account_id = "a1",
                 .symbol = "BTCUSDT",
                 .side = Side::Sell,
                 .price = 100.0,
                 .quantity = 1.0,
                 .sequence = 1,
             }).accepted);
  ASSERT_TRUE(service.Submit(Order{
                 .order_id = "buy-1",
                 .account_id = "a2",
                 .symbol = "BTCUSDT",
                 .side = Side::Buy,
                 .price = 101.0,
                 .quantity = 1.0,
                 .sequence = 2,
             }).accepted);

  auto executions = service.RecentExecutions(10);
  ASSERT_EQ(executions.size(), 1);
  EXPECT_EQ(executions[0].event_id, 1);
  EXPECT_EQ(executions[0].trade.maker_order_id, "sell-1");
  EXPECT_EQ(executions[0].trade.taker_order_id, "buy-1");

  auto a1 = service.RecentExecutionsForAccount("a1", 10);
  ASSERT_EQ(a1.size(), 1);
  EXPECT_EQ(a1[0].trade.maker_account_id, "a1");

  auto missing = service.RecentExecutionsForAccount("none", 10);
  EXPECT_TRUE(missing.empty());
}

TEST(OrderServiceTest, MaintainsIndependentBooksPerSymbol) {
  OrderService service;
  ASSERT_TRUE(service.Submit(Order{
                 .order_id = "btc-buy-1",
                 .account_id = "a1",
                 .symbol = "BTCUSDT",
                 .side = Side::Buy,
                 .price = 100.0,
                 .quantity = 1.0,
                 .sequence = 1,
             }).accepted);
  ASSERT_TRUE(service.Submit(Order{
                 .order_id = "eth-buy-1",
                 .account_id = "a2",
                 .symbol = "ETHUSDT",
                 .side = Side::Buy,
                 .price = 2000.0,
                 .quantity = 2.0,
                 .sequence = 2,
             }).accepted);

  const auto btc = service.SnapshotForSymbol("BTCUSDT", 5);
  const auto eth = service.SnapshotForSymbol("ETHUSDT", 5);

  ASSERT_EQ(btc.bids.size(), 1);
  ASSERT_EQ(eth.bids.size(), 1);
  EXPECT_DOUBLE_EQ(btc.bids[0].price, 100.0);
  EXPECT_DOUBLE_EQ(eth.bids[0].price, 2000.0);

  const auto stats = service.Stats();
  EXPECT_EQ(stats.symbols, 2);
  EXPECT_EQ(stats.live_orders, 2);
}

TEST(OrderServiceTest, SnapshotForUnknownSymbolIsEmpty) {
  OrderService service;
  ASSERT_TRUE(service.Submit(Order{
                 .order_id = "btc-buy-1",
                 .account_id = "a1",
                 .symbol = "BTCUSDT",
                 .side = Side::Buy,
                 .price = 100.0,
                 .quantity = 1.0,
                 .sequence = 1,
             }).accepted);

  const auto unknown = service.SnapshotForSymbol("SOLUSDT", 5);
  EXPECT_TRUE(unknown.bids.empty());
  EXPECT_TRUE(unknown.asks.empty());
}

TEST(OrderServiceTest, ViewForSymbolCombinesStatsAndSnapshot) {
  OrderService service;
  ASSERT_TRUE(service.Submit(Order{
                 .order_id = "btc-buy-1",
                 .account_id = "a1",
                 .symbol = "BTCUSDT",
                 .side = Side::Buy,
                 .price = 100.0,
                 .quantity = 1.0,
                 .sequence = 1,
             }).accepted);

  const auto view = service.ViewForSymbol("BTCUSDT", 5);

  ASSERT_TRUE(view.has_value());
  EXPECT_EQ(view->symbol, "BTCUSDT");
  EXPECT_EQ(view->stats.live_orders, 1);
  EXPECT_EQ(view->stats.trade_count, 0);
  ASSERT_TRUE(view->stats.best_bid.has_value());
  EXPECT_DOUBLE_EQ(*view->stats.best_bid, 100.0);
  ASSERT_EQ(view->order_book.bids.size(), 1);
  EXPECT_DOUBLE_EQ(view->order_book.bids[0].price, 100.0);
}

TEST(OrderServiceTest, ExposesStatsAndSnapshot) {
  OrderService service;
  ASSERT_TRUE(service.Submit(Order{
                 .order_id = "buy-1",
                 .account_id = "a1",
                 .symbol = "BTCUSDT",
                 .side = Side::Buy,
                 .price = 100.0,
                 .quantity = 2.0,
                 .sequence = 1,
             }).accepted);

  auto stats = service.Stats();
  EXPECT_EQ(stats.live_orders, 1);
  EXPECT_EQ(stats.trade_count, 0);
  EXPECT_EQ(stats.tracked_orders, 1);
  EXPECT_EQ(stats.rejected_orders, 0);
  ASSERT_TRUE(stats.best_bid.has_value());
  EXPECT_DOUBLE_EQ(*stats.best_bid, 100.0);
  EXPECT_FALSE(stats.best_ask.has_value());

  auto snapshot = service.Snapshot(3);
  ASSERT_EQ(snapshot.bids.size(), 1);
  EXPECT_DOUBLE_EQ(snapshot.bids[0].total_quantity, 2.0);
}

TEST(OrderServiceTest, TracksOrderLifecycleState) {
  OrderService service;

  auto sell = service.Submit(Order{
      .order_id = "sell-1",
      .account_id = "maker",
      .symbol = "BTCUSDT",
      .side = Side::Sell,
      .price = 100.0,
      .quantity = 2.0,
      .sequence = 1,
  });
  ASSERT_TRUE(sell.accepted);

  auto buy = service.Submit(Order{
      .order_id = "buy-1",
      .account_id = "taker",
      .symbol = "BTCUSDT",
      .side = Side::Buy,
      .price = 101.0,
      .quantity = 1.0,
      .sequence = 2,
  });
  ASSERT_TRUE(buy.accepted);

  auto maker = service.GetOrder("sell-1");
  ASSERT_TRUE(maker.has_value());
  EXPECT_EQ(maker->status, OrderStatus::PartiallyFilled);
  EXPECT_DOUBLE_EQ(maker->filled_quantity, 1.0);

  auto taker = service.GetOrder("buy-1");
  ASSERT_TRUE(taker.has_value());
  EXPECT_EQ(taker->status, OrderStatus::Filled);
  EXPECT_DOUBLE_EQ(taker->filled_quantity, 1.0);

  EXPECT_TRUE(service.Cancel("sell-1"));
  maker = service.GetOrder("sell-1");
  ASSERT_TRUE(maker.has_value());
  EXPECT_EQ(maker->status, OrderStatus::Canceled);
}

TEST(OrderServiceTest, StoresRejectedOrders) {
  OrderService service;
  ASSERT_TRUE(service.Submit(Order{
                 .order_id = "buy-1",
                 .account_id = "a1",
                 .symbol = "BTCUSDT",
                 .side = Side::Buy,
                 .price = 100.0,
                 .quantity = 1.0,
                 .sequence = 5,
             }).accepted);

  auto rejected = service.Submit(Order{
      .order_id = "sell-2",
      .account_id = "a2",
      .symbol = "BTCUSDT",
      .side = Side::Sell,
      .price = 99.0,
      .quantity = 1.0,
      .sequence = 4,
  });
  ASSERT_FALSE(rejected.accepted);

  auto bad = service.GetOrder("sell-2");
  ASSERT_TRUE(bad.has_value());
  EXPECT_EQ(bad->status, OrderStatus::Rejected);
  EXPECT_EQ(bad->reason, "non-monotonic sequence");
}
