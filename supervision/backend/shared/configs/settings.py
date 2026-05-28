from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_", extra="ignore")

    name: str = "TrafficPerceptionEngine"
    env: str = "development"
    debug: bool = True
    host: str = "127.0.0.1"
    port: int = 8000


class DatabaseConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    url: str = Field(default="sqlite+aiosqlite:///./traffic_perception.db", alias="DATABASE_URL")


class CVConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    yolo_model: str = Field(default="yolo11n.pt", alias="YOLO_MODEL")
    yolo_device: str = Field(default="mps", alias="YOLO_DEVICE")
    confidence_threshold: float = Field(default=0.25, alias="CONFIDENCE_THRESHOLD")
    iou_threshold: float = Field(default=0.45, alias="IOU_THRESHOLD")


class LLMConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    enabled: bool = Field(default=False, alias="LLM_ENABLED")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    temperature: float = 0.3


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app: AppConfig = Field(default_factory=AppConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    cv: CVConfig = Field(default_factory=CVConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
