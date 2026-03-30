use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize)]
pub(super) struct StrategySummaryPayload {
    pub(super) strategy_base_url: String,
    pub(super) symbol: String,
    pub(super) source: String,
    pub(super) recent_limit: u64,
    pub(super) orderbook_depth: u64,
    pub(super) aggregation_mode: &'static str,
    pub(super) signal: SummaryComponentEnvelope,
    pub(super) recent_signals: SummaryComponentEnvelope,
    pub(super) persistence: SummaryComponentEnvelope,
    pub(super) matching_orderbook: SummaryComponentEnvelope,
    pub(super) inference_status: SummaryComponentEnvelope,
}

impl StrategySummaryPayload {
    pub(super) fn into_value(self) -> serde_json::Value {
        serde_json::to_value(self).expect("strategy summary payload must always serialize to json")
    }
}

#[derive(Debug, Clone, Serialize)]
pub(super) struct SummaryComponentEnvelope {
    pub(super) ok: bool,
    pub(super) status_code: u16,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(super) url: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(super) payload: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(super) error: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(super) retry_after_ms: Option<u64>,
}

#[derive(Debug, Deserialize)]
pub(super) struct AggregateSummaryPayload {
    #[serde(default)]
    pub(super) symbol: Option<String>,
    #[serde(default)]
    pub(super) source: Option<String>,
    #[serde(default)]
    pub(super) recent_limit: Option<u64>,
    #[serde(default)]
    pub(super) orderbook_depth: Option<u64>,
    pub(super) signal: AggregateSummaryComponent,
    pub(super) recent_signals: AggregateSummaryComponent,
    pub(super) persistence: AggregateSummaryComponent,
    pub(super) matching_orderbook: AggregateSummaryComponent,
    #[serde(default)]
    pub(super) inference_status: Option<AggregateSummaryComponent>,
}

impl AggregateSummaryPayload {
    pub(super) fn has_required_components(&self) -> bool {
        self.signal.has_required_shape()
            && self.recent_signals.has_required_shape()
            && self.persistence.has_required_shape()
            && self.matching_orderbook.has_required_shape()
    }
}

#[derive(Debug, Clone, Deserialize)]
pub(super) struct AggregateSummaryComponent {
    pub(super) ok: bool,
    pub(super) status_code: u16,
    #[serde(default)]
    pub(super) payload: Option<serde_json::Value>,
    #[serde(default)]
    pub(super) error: Option<serde_json::Value>,
    #[serde(default)]
    pub(super) retry_after_ms: Option<u64>,
}

impl AggregateSummaryComponent {
    fn has_required_shape(&self) -> bool {
        self.payload.is_some() || self.error.is_some()
    }
}

#[cfg(test)]
mod tests {
    use super::{AggregateSummaryComponent, AggregateSummaryPayload};

    fn component() -> AggregateSummaryComponent {
        AggregateSummaryComponent {
            ok: true,
            status_code: 200,
            payload: Some(serde_json::json!({"ok": true})),
            error: None,
            retry_after_ms: None,
        }
    }

    #[test]
    fn aggregate_payload_accepts_missing_optional_inference_component() {
        let payload = AggregateSummaryPayload {
            symbol: None,
            source: None,
            recent_limit: None,
            orderbook_depth: None,
            signal: component(),
            recent_signals: component(),
            persistence: component(),
            matching_orderbook: component(),
            inference_status: None,
        };

        assert!(payload.has_required_components());
    }
}
