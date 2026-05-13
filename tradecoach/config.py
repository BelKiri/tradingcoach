"""
Application settings loaded from environment variables.

Uses pydantic-settings to validate and type-check all config.
Load .env file automatically if present.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Supabase
    supabase_url: str
    supabase_key: str  # anon/public key (used with RLS)
    supabase_service_role_key: str = ""  # service role key (bypasses RLS)

    # OpenAI
    openai_api_key: str = ""

    # Anthropic
    anthropic_api_key: str = ""

    # Market data
    twelvedata_api_key: str = ""
    finnhub_api_key: str = ""

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # App settings
    app_env: str = "development"  # development | staging | production
    debug: bool = True
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()  # type: ignore[call-arg]
