use crate::gateway_types::{FirebaseAuthConfig, JwtAuthConfig};
use crate::gateway_utils::{env_flag, non_empty_env};

pub(crate) fn load_jwt_auth_config(app_env: &str) -> JwtAuthConfig {
    JwtAuthConfig {
        enabled: env_flag("JWT_AUTH_ENABLED", false),
        require_in_production: env_flag("JWT_AUTH_REQUIRE_IN_PRODUCTION", true),
        environment: app_env.to_string(),
        hs256_secret: non_empty_env("JWT_HS256_SECRET"),
        issuer: non_empty_env("JWT_ISSUER"),
        audience: non_empty_env("JWT_AUDIENCE"),
    }
}

pub(crate) fn load_firebase_auth_config() -> FirebaseAuthConfig {
    FirebaseAuthConfig {
        required: env_flag("FIREBASE_AUTH_REQUIRED", false),
        project_id: non_empty_env("FIREBASE_PROJECT_ID"),
        web_api_key: non_empty_env("FIREBASE_WEB_API_KEY"),
    }
}
