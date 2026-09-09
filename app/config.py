from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # LLM API keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""

    # LLM model names (configurable so they can be updated without code changes)
    openai_model: str = "gpt-4.1-mini"
    anthropic_model: str = "claude-haiku-4-5-20251001"
    gemini_model: str = "gemini-3.5-flash"

    # Repository ingestion limits
    default_branch: str = "main"
    max_files: int = 30
    max_file_bytes: int = 20_000

    # CORS — set to React dev server origin
    frontend_origin: str = "http://localhost:5173"

    # Storage
    reports_dir: Path = Path("reports")
    temp_dir: Path = Path(".tmp")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def available_providers(self) -> list[str]:
        """Return list of provider names that have API keys configured."""
        providers = []
        if self.openai_api_key:
            providers.append("openai")
        if self.anthropic_api_key:
            providers.append("anthropic")
        if self.gemini_api_key:
            providers.append("gemini")
        return providers


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    settings.temp_dir.mkdir(parents=True, exist_ok=True)
    return settings
