use crate::gateway_types::{parse_market_symbols, DEFAULT_MARKET_SYMBOLS};

pub(crate) fn build_binance_market_ws_url(
    symbols: &[String],
    stream_base: &str,
    stream_suffix: &str,
) -> String {
    let normalized = if symbols.is_empty() {
        parse_market_symbols(DEFAULT_MARKET_SYMBOLS)
    } else {
        symbols.to_vec()
    };
    let streams = normalized
        .iter()
        .map(|symbol| format!("{}{}", symbol.to_ascii_lowercase(), stream_suffix))
        .collect::<Vec<_>>()
        .join("/");
    format!("{}?streams={}", stream_base.trim_end_matches('/'), streams)
}
