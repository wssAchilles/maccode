from __future__ import annotations

import os
from pathlib import Path


def csv_env(name: str, default: str) -> list[str]:
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


class BaseConfig:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    SERVICE_NAME = os.getenv("SERVICE_NAME", "analytics-api")
    API_VERSION = "v1"
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-secret")
    METRIC_CACHE_DIR = Path(os.getenv("METRIC_CACHE_DIR", PROJECT_ROOT / "data" / "cache"))
    JOB_DB_PATH = Path(os.getenv("JOB_DB_PATH", PROJECT_ROOT / "data" / "platform.db"))
    RAW_DATA_PATH = Path(os.getenv("RAW_DATA_PATH", PROJECT_ROOT / "data" / "sample" / "ecommerce_events.csv"))
    SPARK_CONFIG_PATH = Path(os.getenv("SPARK_CONFIG_PATH", PROJECT_ROOT / "configs" / "local.yaml"))
    CORS_ALLOWED_ORIGINS = csv_env(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    API_TIMEOUT_SECONDS = int(os.getenv("API_TIMEOUT_SECONDS", "30"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    TESTING = False


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    ENV_NAME = "development"


class TestingConfig(BaseConfig):
    TESTING = True
    DEBUG = False
    ENV_NAME = "testing"


class ProductionConfig(BaseConfig):
    DEBUG = False
    ENV_NAME = "production"


CONFIG_BY_ENV = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def config_from_env():
    env_name = os.getenv("APP_ENV", "development").lower()
    return CONFIG_BY_ENV.get(env_name, DevelopmentConfig)
