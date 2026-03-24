pub(crate) fn should_publish_legacy_channel(legacy_channel: &str, event_symbol: &str) -> bool {
    let parts = legacy_channel.split('.').collect::<Vec<_>>();
    if let Some(last) = parts.last() {
        // Channels shaped like md.orderbook.BTCUSDT should only receive matching symbol events.
        if last
            .chars()
            .all(|ch| ch.is_ascii_uppercase() || ch.is_ascii_digit())
        {
            return *last == event_symbol;
        }
    }
    true
}
