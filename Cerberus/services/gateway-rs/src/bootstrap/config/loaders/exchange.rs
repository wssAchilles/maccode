use std::env;

use crate::gateway_types::{
    ExchangeConfig, DEFAULT_ALPACA_TRADING_BASE, DEFAULT_BINANCE_API_BASE,
    DEFAULT_BINANCE_ORDER_TEST_PATH,
};
use crate::gateway_utils::non_empty_env;

pub(crate) fn load_exchange_config() -> ExchangeConfig {
    ExchangeConfig {
        binance_api_base: env::var("BINANCE_API_BASE")
            .unwrap_or_else(|_| DEFAULT_BINANCE_API_BASE.to_string()),
        binance_order_test_path: env::var("BINANCE_ORDER_TEST_PATH")
            .unwrap_or_else(|_| DEFAULT_BINANCE_ORDER_TEST_PATH.to_string()),
        binance_api_key: non_empty_env("BINANCE_API_KEY"),
        binance_api_secret: non_empty_env("BINANCE_API_SECRET"),
        alpaca_trading_base: env::var("ALPACA_TRADING_BASE_URL")
            .unwrap_or_else(|_| DEFAULT_ALPACA_TRADING_BASE.to_string()),
        alpaca_api_key: non_empty_env("ALPACA_API_KEY"),
        alpaca_api_secret: non_empty_env("ALPACA_API_SECRET"),
    }
}
