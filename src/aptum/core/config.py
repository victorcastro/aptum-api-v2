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
    # Comma-separated browser origins allowed to call the API. Empty disables CORS.
    cors_origins: str = ""
    # Release 1.1.0 ATS CV pipeline (skill categories in the CV, ATS PDF, generation rules,
    # fidelity check, keyword coverage). Off: CV export behaves exactly as in 1.0.0.
    ats_cv_enabled: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
