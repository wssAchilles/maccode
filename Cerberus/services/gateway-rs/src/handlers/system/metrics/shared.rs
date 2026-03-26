pub(super) fn latency_p95_ms(samples: &std::collections::VecDeque<u64>) -> f64 {
    if samples.is_empty() {
        return 0.0;
    }
    let mut values = samples.iter().copied().collect::<Vec<_>>();
    values.sort_unstable();
    let idx = ((values.len() as f64) * 0.95).ceil() as usize;
    let pos = idx.saturating_sub(1).min(values.len() - 1);
    values[pos] as f64
}
