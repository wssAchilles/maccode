use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub(crate) struct MarketEvent {
    pub(crate) symbol: String,
    pub(crate) bid_price: String,
    pub(crate) ask_price: String,
    pub(crate) event_time: u64,
}

#[derive(Debug, Deserialize)]
pub(crate) struct BinanceBookTicker {
    #[serde(rename = "s")]
    pub(crate) symbol: String,
    #[serde(rename = "b")]
    pub(crate) bid_price: String,
    #[serde(rename = "a")]
    pub(crate) ask_price: String,
    #[serde(rename = "E")]
    pub(crate) event_time: Option<u64>,
}

#[derive(Debug, Deserialize)]
pub(crate) struct BinanceCombinedStream<T> {
    pub(crate) data: T,
}

#[derive(Debug, Deserialize)]
pub(crate) struct KlineQuery {
    pub(crate) symbol: Option<String>,
    pub(crate) interval: Option<String>,
    pub(crate) limit: Option<u16>,
}

#[derive(Debug, Deserialize)]
pub(crate) struct SnapshotQuery {
    pub(crate) symbol: Option<String>,
}

#[derive(Debug, Deserialize)]
pub(crate) struct BinanceRuleQuery {
    pub(crate) symbol: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub(crate) struct OrderEvent {
    pub(crate) channel: String,
    pub(crate) payload: serde_json::Value,
    pub(crate) received_at: u64,
}

#[derive(Debug, Deserialize)]
pub(crate) struct RecentOrdersQuery {
    pub(crate) limit: Option<usize>,
    pub(crate) channel: Option<String>,
    pub(crate) account_id: Option<String>,
    pub(crate) symbol: Option<String>,
    pub(crate) order_id: Option<String>,
    pub(crate) status: Option<String>,
    pub(crate) request_id: Option<String>,
}

#[derive(Debug, Deserialize)]
pub(crate) struct StrategySummaryQuery {
    pub(crate) symbol: Option<String>,
    pub(crate) recent_limit: Option<u16>,
    pub(crate) source: Option<String>,
    pub(crate) orderbook_depth: Option<u16>,
}

#[derive(Debug, Deserialize)]
pub(crate) struct BinanceTestOrderRequest {
    pub(crate) symbol: String,
    pub(crate) side: String,
    #[serde(default = "default_binance_order_type")]
    pub(crate) order_type: String,
    pub(crate) quantity: String,
    pub(crate) price: Option<String>,
    pub(crate) time_in_force: Option<String>,
    pub(crate) recv_window: Option<u64>,
}

#[derive(Debug, Deserialize)]
pub(crate) struct AlpacaOrderRequest {
    pub(crate) symbol: String,
    pub(crate) qty: String,
    pub(crate) side: String,
    #[serde(rename = "type")]
    pub(crate) order_type: String,
    pub(crate) time_in_force: String,
    pub(crate) limit_price: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub(crate) struct BinanceSymbolRule {
    pub(crate) symbol: String,
    pub(crate) min_notional: Option<f64>,
    pub(crate) min_qty: Option<f64>,
    pub(crate) step_size: Option<f64>,
    pub(crate) tick_size: Option<f64>,
    pub(crate) refreshed_at: u64,
}

pub(crate) fn default_binance_order_type() -> String {
    "LIMIT".to_string()
}
