from functools import lru_cache
from typing import List

from pydantic import EmailStr, PositiveInt, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    COHERE: str
    TAVILY_SEARCH: str

    TELEGRAM_BOT_TOKEN: str

    ADMINS: List[PositiveInt]

    SENDER_EMAIL: EmailStr
    GMAIL_APP_PASSWORD: str

    SESSION_SECRET_KEY: str
    REDIS_URL: str = "redis://localhost:6379"

    model_config = SettingsConfigDict(env_file=".env")

    @field_validator("ADMINS", mode="before")
    def parse_admins(cls, v):
        if isinstance(v, str):
            return [int(x) for x in v.split(",")]
        return v


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()
