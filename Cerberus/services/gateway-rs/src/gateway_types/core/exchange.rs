use crate::gateway_types::BinanceSymbolRule;

#[derive(Clone, Default)]
pub(crate) struct ExchangeConfig {
    pub(crate) binance_api_base: String,
    pub(crate) binance_order_test_path: String,
    pub(crate) binance_api_key: Option<String>,
    pub(crate) binance_api_secret: Option<String>,
    pub(crate) alpaca_trading_base: String,
    pub(crate) alpaca_api_key: Option<String>,
    pub(crate) alpaca_api_secret: Option<String>,
}

#[derive(Debug, Clone)]
pub(crate) struct CachedBinanceSymbolRule {
    pub(crate) rule: BinanceSymbolRule,
    pub(crate) cached_at: u64,
}
