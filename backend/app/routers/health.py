from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import Settings, get_settings

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    app_env: str
    config_ready: bool
    providers: dict[str, bool]
    database_configured: bool
    storage_configured: bool


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: Settings = Depends(get_settings)) -> HealthResponse:
    providers = settings.provider_readiness
    database_configured = bool(settings.database_url)
    storage_configured = bool(settings.storage_root)

    return HealthResponse(
        status="ok",
        app_env=settings.app_env,
        config_ready=all(providers.values()) and database_configured and storage_configured,
        providers=providers,
        database_configured=database_configured,
        storage_configured=storage_configured,
    )
