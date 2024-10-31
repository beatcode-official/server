import json
from functools import lru_cache
from typing import Dict

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # General
    PROJECT_NAME: str = "Beatcode"
    VERSION: str = "1.0.0"
    API_STR: str = "/api"

    # Email
    RESEND_API_KEY: str
    FROM_EMAIL: str
    FRONTEND_URL: str
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int

    # Database
    DATABASE_URL: str

    # JWT
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    ALGORITHM: str

    # Code Execution
    MAX_CONCURRENT_EASY: int
    MAX_CONCURRENT_MEDIUM: int
    MAX_CONCURRENT_HARD: int

    # Docker Settings
    DOCKER_IMAGE: str
    DOCKER_MEMORY_LIMIT_EASY: int
    DOCKER_MEMORY_LIMIT_MEDIUM: int
    DOCKER_MEMORY_LIMIT_HARD: int
    DOCKER_TIME_LIMIT_EASY: int
    DOCKER_TIME_LIMIT_MEDIUM: int
    DOCKER_TIME_LIMIT_HARD: int
    DOCKER_CPU_LIMIT: float

    # Rate Limiting
    SUBMISSION_COOLDOWN: int  # seconds

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
