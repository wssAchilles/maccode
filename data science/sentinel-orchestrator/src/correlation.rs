use std::{
    sync::{
        Arc,
        atomic::{AtomicU64, Ordering},
    },
    time::{SystemTime, UNIX_EPOCH},
};

use axum::http::HeaderMap;

pub const CORRELATION_ID_HEADER: &str = "x-correlation-id";

#[derive(Clone, Default)]
pub struct CorrelationIdGenerator {
    sequence: Arc<AtomicU64>,
    last_issued_at_ms: Arc<AtomicU64>,
    last_issued_sequence: Arc<AtomicU64>,
}

impl CorrelationIdGenerator {
    #[must_use]
    pub fn resolve_or_generate(&self, headers: &HeaderMap) -> String {
        headers
            .get(CORRELATION_ID_HEADER)
            .and_then(|value| value.to_str().ok())
            .map(str::trim)
            .filter(|value| !value.is_empty())
            .map(ToOwned::to_owned)
            .unwrap_or_else(|| self.generate())
    }

    #[must_use]
    pub fn generate(&self) -> String {
        let issued_at_ms = now_ms();
        let sequence = self.sequence.fetch_add(1, Ordering::Relaxed) + 1;
        self.last_issued_at_ms
            .store(issued_at_ms, Ordering::Relaxed);
        self.last_issued_sequence.store(sequence, Ordering::Relaxed);
        format!("cp-{issued_at_ms}-{sequence}")
    }

    #[must_use]
    pub fn last_issued(&self) -> Option<String> {
        let issued_at_ms = self.last_issued_at_ms.load(Ordering::Relaxed);
        let sequence = self.last_issued_sequence.load(Ordering::Relaxed);
        if issued_at_ms == 0 || sequence == 0 {
            return None;
        }
        Some(format!("cp-{issued_at_ms}-{sequence}"))
    }
}

fn now_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis() as u64
}

#[cfg(test)]
mod tests {
    use axum::http::{HeaderMap, HeaderValue};

    use super::{CORRELATION_ID_HEADER, CorrelationIdGenerator};

    #[test]
    fn generate_records_last_issued_correlation_id() {
        let generator = CorrelationIdGenerator::default();
        let generated = generator.generate();

        assert!(generated.starts_with("cp-"));
        assert_eq!(generator.last_issued().as_deref(), Some(generated.as_str()));
    }

    #[test]
    fn resolve_or_generate_prefers_incoming_header() {
        let generator = CorrelationIdGenerator::default();
        let mut headers = HeaderMap::new();
        headers.insert(
            CORRELATION_ID_HEADER,
            HeaderValue::from_static("external-correlation-id"),
        );

        assert_eq!(
            generator.resolve_or_generate(&headers),
            "external-correlation-id"
        );
        assert!(generator.last_issued().is_none());
    }
}
