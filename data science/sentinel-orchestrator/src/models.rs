use serde::Deserialize;

#[derive(Debug, Deserialize)]
pub struct OperationEnvelope<T> {
    pub data: T,
}
