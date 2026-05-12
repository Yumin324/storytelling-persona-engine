from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import Settings, get_settings

router = APIRouter()

REQUIRED_ENV_EXAMPLE_KEYS = {
    "APP_ENV",
    "DATABASE_URL",
    "STORAGE_ROOT",
    "OPENAI_API_KEY",
    "OPENAI_LLM_MODEL",
    "OPENAI_IMAGE_MODEL",
    "KLING_API_KEY",
    "KLING_ACCESS_KEY",
    "KLING_SECRET_KEY",
    "KLING_API_BASE_URL",
    "KLING_VIDEO_MODEL",
    "ELEVENLABS_API_KEY",
    "ELEVENLABS_DEFAULT_MODEL",
    "API_TIMEOUT_LLM_SECONDS",
    "API_TIMEOUT_IMAGE_SECONDS",
    "API_TIMEOUT_VIDEO_CREATE_SECONDS",
    "API_TIMEOUT_VIDEO_POLL_TOTAL_SECONDS",
    "API_TIMEOUT_VOICE_SECONDS",
    "API_RETRY_COUNT",
    "PRODUCTION_SCENE_CONCURRENCY",
}


class HealthResponse(BaseModel):
    status: str
    app_env: str
    config_ready: bool
    providers: dict[str, bool]
    missing_config: list[str]
    env_example_complete: bool
    env_example_missing: list[str]
    database_configured: bool
    storage_configured: bool


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: Settings = Depends(get_settings)) -> HealthResponse:
    providers = settings.provider_readiness
    database_configured = bool(settings.database_url)
    storage_configured = bool(settings.storage_root)
    missing_config = missing_runtime_config(settings)
    env_example_missing = missing_env_example_keys()

    return HealthResponse(
        status="ok",
        app_env=settings.app_env,
        config_ready=not missing_config and database_configured and storage_configured,
        providers=providers,
        missing_config=missing_config,
        env_example_complete=not env_example_missing,
        env_example_missing=env_example_missing,
        database_configured=database_configured,
        storage_configured=storage_configured,
    )


def missing_runtime_config(settings: Settings) -> list[str]:
    missing = []
    checks = {
        "OPENAI_API_KEY": settings.openai_api_key,
        "KLING_API_BASE_URL": settings.kling_api_base_url,
        "ELEVENLABS_API_KEY": settings.elevenlabs_api_key,
        "DATABASE_URL": settings.database_url,
        "STORAGE_ROOT": settings.storage_root,
    }
    for key, value in checks.items():
        if not value:
            missing.append(key)
    if not settings.kling_api_key and not (settings.kling_access_key and settings.kling_secret_key):
        missing.append("KLING_API_KEY or KLING_ACCESS_KEY/KLING_SECRET_KEY")
    return missing


def missing_env_example_keys() -> list[str]:
    env_example = Path(__file__).resolve().parents[3] / ".env.example"
    if not env_example.exists():
        return sorted(REQUIRED_ENV_EXAMPLE_KEYS)

    found = set()
    for line in env_example.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        found.add(stripped.split("=", 1)[0])
    return sorted(REQUIRED_ENV_EXAMPLE_KEYS - found)
