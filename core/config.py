from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "NextQuest"
    app_version: str = "1.0.0"
    environment: Literal["development", "production", "test"] = "development"

    database_url: str = "sqlite:///./nextquest.db"

    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    # OPENAI_KEY is accepted too, because that is what the OpenAI dashboard
    # suggests when you copy a key straight into a .env file.
    openai_api_key: str | None = Field(
        default=None, validation_alias=AliasChoices("openai_api_key", "openai_key")
    )
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = Field(default=0.8, ge=0.0, le=2.0)
    openai_timeout: int = 60

    # Optional LangSmith tracing for inspecting chain runs.
    langchain_api_key: str | None = Field(
        default=None, validation_alias=AliasChoices("langchain_api_key", "langchain_key")
    )
    langchain_project: str = "nextquest"

    cors_origins: list[str] = ["*"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def llm_enabled(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def tracing_enabled(self) -> bool:
        return bool(self.langchain_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
