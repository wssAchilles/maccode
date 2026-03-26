use std::env;

#[derive(Debug, Clone)]
pub(crate) struct BootstrapRuntime {
    pub(crate) port: String,
    pub(crate) cors_allow_origins: String,
    pub(crate) app_env: String,
}

pub(crate) fn load_bootstrap_runtime() -> BootstrapRuntime {
    BootstrapRuntime {
        port: env::var("PORT").unwrap_or_else(|_| "8080".to_string()),
        cors_allow_origins: env::var("CORS_ALLOW_ORIGINS").unwrap_or_else(|_| "*".to_string()),
        app_env: env::var("APP_ENV").unwrap_or_else(|_| "development".to_string()),
    }
}
