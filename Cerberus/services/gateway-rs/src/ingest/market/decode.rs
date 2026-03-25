use crate::gateway_types::{BinanceBookTicker, BinanceCombinedStream, MarketEvent};

pub(super) fn parse_market_event(raw: &str) -> Option<MarketEvent> {
    let tick: BinanceBookTicker = if let Ok(combined) =
        serde_json::from_str::<BinanceCombinedStream<BinanceBookTicker>>(raw)
    {
        combined.data
    } else if let Ok(value) = serde_json::from_str::<BinanceBookTicker>(raw) {
        value
    } else {
        return None;
    };

    Some(MarketEvent {
        symbol: tick.symbol,
        bid_price: tick.bid_price,
        ask_price: tick.ask_price,
        event_time: tick.event_time.unwrap_or_default(),
    })
}
