from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = Field(default="development", alias="APP_ENV")
    database_url: str = Field(default="sqlite:///./ugclabs.db", alias="DATABASE_URL")
    storage_root: str = Field(default="./storage", alias="STORAGE_ROOT")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_llm_model: str = Field(default="gpt-5.2", alias="OPENAI_LLM_MODEL")
    openai_image_model: str = Field(default="gpt-image-2", alias="OPENAI_IMAGE_MODEL")

    kling_api_key: str = Field(default="", alias="KLING_API_KEY")
    kling_access_key: str = Field(default="", alias="KLING_ACCESS_KEY")
    kling_secret_key: str = Field(default="", alias="KLING_SECRET_KEY")
    kling_api_base_url: str = Field(default="", alias="KLING_API_BASE_URL")
    kling_video_model: str = Field(default="kling-v3", alias="KLING_VIDEO_MODEL")

    elevenlabs_api_key: str = Field(default="", alias="ELEVENLABS_API_KEY")
    elevenlabs_default_model: str = Field(default="", alias="ELEVENLABS_DEFAULT_MODEL")

    api_timeout_llm_seconds: int = Field(default=120, alias="API_TIMEOUT_LLM_SECONDS")
    api_timeout_image_seconds: int = Field(default=600, alias="API_TIMEOUT_IMAGE_SECONDS")
    api_timeout_video_create_seconds: int = Field(default=120, alias="API_TIMEOUT_VIDEO_CREATE_SECONDS")
    api_timeout_video_poll_total_seconds: int = Field(default=1200, alias="API_TIMEOUT_VIDEO_POLL_TOTAL_SECONDS")
    api_timeout_voice_seconds: int = Field(default=120, alias="API_TIMEOUT_VOICE_SECONDS")
    api_retry_count: int = Field(default=3, alias="API_RETRY_COUNT")
    production_scene_concurrency: int = Field(default=2, alias="PRODUCTION_SCENE_CONCURRENCY")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def provider_readiness(self) -> dict[str, bool]:
        return {
            "openai": bool(self.openai_api_key),
            "kling": bool((self.kling_api_key or (self.kling_access_key and self.kling_secret_key)) and self.kling_api_base_url),
            "elevenlabs": bool(self.elevenlabs_api_key),
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
