mod codes;
mod envelope;

pub(crate) use codes::GatewayErrorCode;
pub(crate) use envelope::{error_body, error_body_code, internal_err_json, with_request_context};
