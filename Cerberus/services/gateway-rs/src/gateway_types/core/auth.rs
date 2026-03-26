#[derive(Clone, Default)]
pub(crate) struct FirebaseAuthConfig {
    pub(crate) required: bool,
    pub(crate) project_id: Option<String>,
    pub(crate) web_api_key: Option<String>,
}

#[derive(Clone, Default)]
pub(crate) struct JwtAuthConfig {
    pub(crate) enabled: bool,
    pub(crate) require_in_production: bool,
    pub(crate) environment: String,
    pub(crate) hs256_secret: Option<String>,
    pub(crate) issuer: Option<String>,
    pub(crate) audience: Option<String>,
}

impl JwtAuthConfig {
    pub(crate) fn effective_required(&self) -> bool {
        if self.enabled {
            return true;
        }
        self.require_in_production && self.environment.eq_ignore_ascii_case("production")
    }
}

#[derive(Clone)]
pub(crate) struct InternalServiceAuthConfig {
    pub(crate) enabled: bool,
    pub(crate) audience: Option<String>,
    pub(crate) metadata_identity_url: String,
    pub(crate) token_cache_ttl_seconds: u64,
}

#[derive(Clone, Debug)]
pub(crate) struct CachedInternalServiceToken {
    pub(crate) token: String,
    pub(crate) expires_at_ms: u64,
}

#[derive(Clone, Debug)]
pub(crate) struct AuthenticatedUser {
    pub(crate) uid: String,
    pub(crate) email: Option<String>,
}

#[derive(Clone, Debug)]
pub(crate) struct CachedAuthUser {
    pub(crate) user: AuthenticatedUser,
    pub(crate) expires_at_ms: u64,
}
