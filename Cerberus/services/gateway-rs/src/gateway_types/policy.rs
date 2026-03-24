use serde::Serialize;

#[derive(Debug, Clone, Serialize)]
pub(crate) struct TradingPolicy {
    pub(crate) enforced: bool,
    pub(crate) binance_allowed_symbols: Vec<String>,
    pub(crate) alpaca_allowed_symbols: Vec<String>,
    pub(crate) max_binance_order_qty: Option<f64>,
    pub(crate) max_binance_order_notional_usd: Option<f64>,
    pub(crate) max_alpaca_order_qty: Option<f64>,
    pub(crate) max_alpaca_limit_notional_usd: Option<f64>,
}

impl TradingPolicy {
    pub(crate) fn from_env(market_symbols: &[String]) -> Self {
        let binance_allowed_symbols = std::env::var("BINANCE_ALLOWED_SYMBOLS")
            .ok()
            .map(|raw| parse_market_symbols(raw.as_str()))
            .filter(|symbols| !symbols.is_empty())
            .unwrap_or_else(|| market_symbols.to_vec());

        let alpaca_allowed_symbols = std::env::var("ALPACA_ALLOWED_SYMBOLS")
            .ok()
            .map(|raw| parse_market_symbols(raw.as_str()))
            .filter(|symbols| !symbols.is_empty())
            .unwrap_or_else(|| vec!["AAPL".to_string(), "TSLA".to_string(), "NVDA".to_string()]);

        Self {
            enforced: parse_env_bool("TRADING_POLICY_ENFORCED", true),
            binance_allowed_symbols,
            alpaca_allowed_symbols,
            max_binance_order_qty: parse_optional_positive_env_f64("MAX_BINANCE_ORDER_QTY"),
            max_binance_order_notional_usd: parse_optional_positive_env_f64(
                "MAX_BINANCE_ORDER_NOTIONAL_USD",
            ),
            max_alpaca_order_qty: parse_optional_positive_env_f64("MAX_ALPACA_ORDER_QTY"),
            max_alpaca_limit_notional_usd: parse_optional_positive_env_f64(
                "MAX_ALPACA_LIMIT_NOTIONAL_USD",
            ),
        }
    }
}

fn parse_env_bool(name: &str, default: bool) -> bool {
    match std::env::var(name) {
        Ok(value) => matches!(
            value.trim().to_ascii_lowercase().as_str(),
            "1" | "true" | "yes" | "on"
        ),
        Err(_) => default,
    }
}

fn parse_optional_positive_env_f64(name: &str) -> Option<f64> {
    std::env::var(name).ok().and_then(|raw| {
        let trimmed = raw.trim();
        if trimmed.is_empty() {
            None
        } else {
            trimmed.parse::<f64>().ok().filter(|value| *value > 0.0)
        }
    })
}

pub(crate) fn parse_market_symbols(raw: &str) -> Vec<String> {
    raw.split(',')
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .map(|s| s.to_ascii_uppercase())
        .collect::<Vec<_>>()
}
