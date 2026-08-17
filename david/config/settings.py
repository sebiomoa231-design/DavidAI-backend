"""
Centralized configuration for David AI.
Loads everything from environment variables / .env exactly once.
No secrets are ever hard-coded here.
"""
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Server ---
    SECRET_KEY: str = "insecure-dev-key-change-me"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENV: str = "development"
    APP_VERSION: str = "1.5.0"

    # --- Owner / Single-user mode ---
    OWNER_EMAIL: str = "sebiomoa231@gmail.com"
    OWNER_DISPLAY_NAME: str = "David AI Creator"
    OWNER_RELATIONSHIP: str = "creator, owner, guardian, friend"
    PRIVATE_MODE: bool = True
    ALLOW_REGISTRATION: bool = False

    # --- Paths ---
    DATA_DIR: Path = BASE_DIR / "data"
    LOG_DIR: Path = BASE_DIR / "logs"
    UPLOAD_DIR: Path = BASE_DIR / "uploads"

    # --- Providers ---
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    HUGGINGFACE_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    CEREBRAS_API_KEY: str = ""
    SAMBANOVA_API_KEY: str = ""

    GEMINI_MODEL: str = "gemini-1.5-flash"
    GROQ_MODEL: str = "llama-3.1-70b-versatile"
    HUGGINGFACE_MODEL: str = "meta-llama/Llama-3.1-8B-Instruct"
    OPENROUTER_MODEL: str = "openrouter/auto"
    CEREBRAS_MODEL: str = "llama3.1-70b"
    SAMBANOVA_MODEL: str = "Meta-Llama-3.1-70B-Instruct"

    # --- Router ---
    ROUTER_MODE: str = "auto"  # auto | manual | smart
    PROVIDER_PRIORITY: str = "gemini,groq,cerebras,sambanova,openrouter,huggingface"

    # --- Database ---
    DATABASE_URL: str = "sqlite:///./data/david.db"

    # --- Auth ---
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    JWT_ALGORITHM: str = "HS256"

    @property
    def provider_priority_list(self) -> List[str]:
        return [p.strip().lower() for p in self.PROVIDER_PRIORITY.split(",") if p.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return settings
