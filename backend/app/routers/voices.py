from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import ProviderError
from app.services.elevenlabs_voice_service import ElevenLabsVoiceService

router = APIRouter()


class VoiceResponse(BaseModel):
    voice_id: str | None
    name: str | None
    provider: str
    category: str | None = None
    description: str | None = None
    labels: dict = Field(default_factory=dict)
    gender: str | None = None
    preview_url: str | None = None


@router.get("/voices", response_model=list[VoiceResponse])
async def list_voices(db: Session = Depends(get_db)) -> list[dict]:
    try:
        return await ElevenLabsVoiceService().list_voices(db=db)
    except ProviderError as exc:
        raise HTTPException(status_code=503, detail=asdict(exc.normalized())) from exc
