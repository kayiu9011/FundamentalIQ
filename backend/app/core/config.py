from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment or the project .env file."""

    app_name: str = "FundamentalIQ"
    fmp_api_key: str = ""
    fmp_base_url: str = "https://financialmodelingprep.com/stable"
    data_provider_mode: Literal["mock", "fmp"] = "mock"
    cache_ttl_seconds: int = Field(default=300, ge=0, le=3600)
    minimum_data_coverage: float = Field(default=60, ge=0, le=100)
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    @property
    def live_ready(self) -> bool:
        return self.data_provider_mode == "fmp" and bool(self.fmp_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()

