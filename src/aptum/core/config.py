from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    log_level: str = "INFO"
    database_url: str
    firebase_project_id: str
    firebase_client_email: str = ""
    firebase_private_key: str = ""
    firebase_check_revoked: bool = False
    openai_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
