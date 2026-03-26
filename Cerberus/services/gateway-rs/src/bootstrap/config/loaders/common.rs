use std::env;

pub(crate) fn parse_env_u64(key: &str) -> Option<u64> {
    env::var(key).ok()?.trim().parse::<u64>().ok()
}

pub(crate) fn parse_env_usize(key: &str) -> Option<usize> {
    env::var(key).ok()?.trim().parse::<usize>().ok()
}

pub(crate) fn parse_env_f64(key: &str) -> Option<f64> {
    env::var(key).ok()?.trim().parse::<f64>().ok()
}
