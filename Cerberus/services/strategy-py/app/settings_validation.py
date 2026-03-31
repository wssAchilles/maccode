from __future__ import annotations

from app.config import settings


class SettingsValidationError(RuntimeError):
    pass


def validate_runtime_settings() -> None:
    errors: list[str] = []

    if settings.firebase_enabled and not (settings.firebase_project_id or "").strip():
        errors.append("firebase_enabled=true requires FIREBASE_PROJECT_ID")

    if settings.supabase_enabled:
        if not (settings.supabase_project_url or "").strip():
            errors.append("supabase_enabled=true requires SUPABASE_PROJECT_URL")
        if not (settings.supabase_service_role_key or "").strip():
            errors.append("supabase_enabled=true requires SUPABASE_SERVICE_ROLE_KEY")

    if settings.matching_enabled and not settings.matching_grpc_target.strip():
        errors.append("matching_enabled=true requires MATCHING_GRPC_TARGET")

    if settings.strategy_conflict_policy not in {
        "review_on_conflict",
        "prefer_priority",
        "prefer_weighted_score",
    }:
        errors.append(
            "strategy_conflict_policy must be one of: review_on_conflict, prefer_priority, prefer_weighted_score"
        )

    if settings.strategy_downgrade_policy not in {"review", "hold"}:
        errors.append("strategy_downgrade_policy must be one of: review, hold")
    if settings.strategy_state_enabled and not settings.strategy_state_key.strip():
        errors.append("strategy_state_key must be non-empty when strategy_state_enabled=true")

    if settings.strategy_rule_priority <= 0:
        errors.append("strategy_rule_priority must be > 0")
    if settings.strategy_inference_priority <= 0:
        errors.append("strategy_inference_priority must be > 0")
    if not settings.strategy_rule_enabled and not settings.strategy_inference_enabled:
        errors.append("at least one strategy source must be enabled")

    for name, value in {
        "strategy_rule_weight_observe": settings.strategy_rule_weight_observe,
        "strategy_inference_weight_observe": settings.strategy_inference_weight_observe,
        "strategy_rule_weight_primary": settings.strategy_rule_weight_primary,
        "strategy_inference_weight_primary": settings.strategy_inference_weight_primary,
    }.items():
        if value < 0:
            errors.append(f"{name} must be >= 0")

    for name, value in {
        "strategy_rule_symbol_coverage": settings.strategy_rule_symbol_coverage,
        "strategy_inference_symbol_coverage": settings.strategy_inference_symbol_coverage,
    }.items():
        if not _symbol_coverage_is_valid(value):
            errors.append(f"{name} must be '*' or a comma-separated symbol list")

    if settings.inference_mode not in {"disabled", "observe", "primary"}:
        errors.append("inference_mode must be one of: disabled, observe, primary")

    if settings.inference_enabled and settings.inference_mode == "disabled":
        errors.append("inference_enabled=true requires inference_mode to be observe or primary")

    if not settings.inference_enabled and settings.inference_mode != "disabled":
        errors.append("inference_mode requires inference_enabled=true")

    if settings.inference_enabled and not settings.inference_model_id.strip():
        errors.append("inference_enabled=true requires INFERENCE_MODEL_ID")

    if settings.inference_enabled and settings.inference_model_source == "google_drive":
        if not settings.inference_artifact_folder_url.strip():
            errors.append(
                "inference_model_source=google_drive requires INFERENCE_ARTIFACT_FOLDER_URL"
            )
    if settings.inference_enabled and settings.inference_model_source == "gcs":
        if not settings.inference_artifact_gcs_uri.strip():
            errors.append(
                "inference_model_source=gcs requires INFERENCE_ARTIFACT_GCS_URI"
            )
    if settings.inference_registry_gcs_uris.strip():
        for raw_uri in settings.inference_registry_gcs_uris.split(","):
            uri = raw_uri.strip()
            if not uri:
                continue
            if not uri.startswith("gs://"):
                errors.append("inference_registry_gcs_uris entries must start with gs://")
    if not 0.0 <= settings.inference_primary_min_macro_f1 <= 1.0:
        errors.append("inference_primary_min_macro_f1 must be between 0 and 1")
    if settings.inference_primary_min_observe_ticks < 0:
        errors.append("inference_primary_min_observe_ticks must be >= 0")
    if not 0.0 <= settings.inference_primary_min_agreement_ratio <= 1.0:
        errors.append("inference_primary_min_agreement_ratio must be between 0 and 1")
    if settings.inference_audit_max_events <= 0:
        errors.append("inference_audit_max_events must be > 0")
    if settings.inference_rollout_state_enabled and not settings.inference_rollout_state_key.strip():
        errors.append("inference_rollout_state_key must be non-empty when inference_rollout_state_enabled=true")
    if settings.inference_rollout_persist_every_observations <= 0:
        errors.append("inference_rollout_persist_every_observations must be > 0")

    if settings.market_stream_enabled and not settings.market_stream_key.strip():
        errors.append("market_stream_enabled=true requires MARKET_STREAM_KEY")

    if settings.event_stream_enabled and not settings.event_stream_key.strip():
        errors.append("event_stream_enabled=true requires EVENT_STREAM_KEY")

    if settings.signal_idempotency_ttl_seconds <= 0:
        errors.append("signal_idempotency_ttl_seconds must be > 0")

    if settings.idempotency_max_entries <= 0:
        errors.append("idempotency_max_entries must be > 0")

    if settings.retriable_base_backoff_seconds <= 0:
        errors.append("retriable_base_backoff_seconds must be > 0")

    if settings.retriable_max_backoff_seconds < settings.retriable_base_backoff_seconds:
        errors.append("retriable_max_backoff_seconds must be >= retriable_base_backoff_seconds")

    if _is_production_env() and settings.cors_allow_origins.strip() == "*":
        errors.append("CORS_ALLOW_ORIGINS cannot be '*' in production")

    if _is_production_env() and settings.market_stream_legacy_pubsub_fallback:
        errors.append("market_stream_legacy_pubsub_fallback must be false in production")
    if _is_production_env() and settings.event_stream_publish_legacy_pubsub:
        errors.append("event_stream_publish_legacy_pubsub must be false in production")

    if errors:
        raise SettingsValidationError("; ".join(errors))


def _is_production_env() -> bool:
    return settings.app_env.strip().lower() == "production"


def _symbol_coverage_is_valid(raw: str) -> bool:
    normalized = raw.strip()
    if not normalized or normalized == "*":
        return True
    return all(item.strip().upper() == item.strip() for item in normalized.split(",") if item.strip())
