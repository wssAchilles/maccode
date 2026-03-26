#[derive(Debug, Clone, Copy)]
pub(crate) enum GatewayErrorCode {
    ValidationError,
    ConfigError,
    UpstreamError,
    UpstreamRequestFailed,
    UpstreamDecodeFailed,
    UpstreamStatusError,
    InternalError,
    AuthRequired,
    AuthVerifyFailed,
    SignatureError,
}

impl GatewayErrorCode {
    pub(crate) const fn as_str(self) -> &'static str {
        match self {
            Self::ValidationError => "validation_error",
            Self::ConfigError => "config_error",
            Self::UpstreamError => "upstream_error",
            Self::UpstreamRequestFailed => "upstream_request_failed",
            Self::UpstreamDecodeFailed => "upstream_decode_failed",
            Self::UpstreamStatusError => "upstream_status_error",
            Self::InternalError => "internal_error",
            Self::AuthRequired => "auth_required",
            Self::AuthVerifyFailed => "auth_verify_failed",
            Self::SignatureError => "signature_error",
        }
    }
}
