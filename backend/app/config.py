from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = Field(default="CRE Sales Intelligence", alias="APP_NAME")
    database_url: str = Field(default="sqlite:///./cre_sales_intelligence.db", alias="DATABASE_URL")
    backend_cors_origins: str = Field(default="http://localhost:3000", alias="BACKEND_CORS_ORIGINS")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    edinet_api_key: str = Field(default="", alias="EDINET_API_KEY")
    ir_fetch_enabled: str = Field(default="false", alias="IR_FETCH_ENABLED")
    ir_analysis_mode: str = Field(default="mock", alias="IR_ANALYSIS_MODE")
    ir_fetch_dry_run: str = Field(default="true", alias="IR_FETCH_DRY_RUN")
    ir_fetch_storage_dir: str = Field(default="./storage/ir_fetch", alias="IR_FETCH_STORAGE_DIR")
    edinet_lookback_days: int = Field(default=365, alias="EDINET_LOOKBACK_DAYS")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def ai_mode(self) -> str:
        return "openai" if self.openai_api_key else "mock"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
