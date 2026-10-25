from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "heartbeat-service"
    app_env: str = "development"
    heartbeat_enabled: bool = True
    heartbeat_interval_seconds: float = 300.0
    heartbeat_log_path: str = "logs/heartbeat.log"
    heartbeat_message: str = "heartbeat"


@lru_cache
def get_settings() -> Settings:
    return Settings()
