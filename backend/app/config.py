from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    google_fact_check_api_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "GOOGLE_FACT_CHECK_API_KEY",
            "GOOGLE_API_KEY",
        ),
    )
    database_url: str = "sqlite:///./fact_check.db"
    secret_key: str = "dev-secret-key"
    feedback_llm_api_key: str = ""
    feedback_llm_base_url: str = "https://api.openai.com/v1"
    feedback_llm_model: str = "gpt-4o-mini"
    feedback_llm_timeout_seconds: float = Field(default=8.0, gt=0, le=30)
    feedback_llm_min_attempts: int = Field(default=4, ge=1, le=100)

    model_config = SettingsConfigDict(
        # .env na raiz do repositório ou em backend/ (o último tem prioridade)
        env_file=(BACKEND_DIR.parent / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        # o .env da raiz pode ter variáveis do frontend (ex.: NEXT_PUBLIC_API_URL)
        extra="ignore",
    )


settings = Settings()
