from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    groq_api_key: str
    groq_model: str = "llama-3.1-8b-instant"
    groq_transcription_model: str = "whisper-large-v3-turbo"
    request_timeout_seconds: float = 45.0
    allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    # En Codespaces o Gitpod el puerto publico cambia en cada sesion, asi que se
    # permiten por patron en lugar de enumerar cada origen en ALLOWED_ORIGINS.
    allowed_origin_regex: str | None = r"https://.*\.(app\.github\.dev|gitpod\.io)"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip().startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    # Los valores llegan del .env en tiempo de ejecucion, asi que el verificador
    # de tipos cree que falta groq_api_key. Pydantic lo resuelve al arrancar.
    return Settings()  # pyright: ignore[reportCallIssue]
