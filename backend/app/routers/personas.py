from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Persona, PersonaGenerationJob, Status
from app.schemas import PersonaCreate, PersonaGenerationJobRead, PersonaRead
from app.services.persona_generation_service import run_persona_generation_job

router = APIRouter()

REQUIRED_PHYSICAL_FIELDS = {
    "ethnicity",
    "skin_tone",
    "face_shape",
    "jawline",
    "cheekbones",
    "eye_shape",
    "eye_color",
    "eyebrow_shape",
    "eyebrow_color",
    "nose_shape",
    "mouth_shape",
    "lip_fullness",
    "hair_length",
    "hair_texture",
    "default_hair_color",
    "facial_hair",
    "body_type",
    "distinguishing_features",
}
REQUIRED_PERSONALITY_FIELDS = {
    "core_personality",
    "content_niche",
    "communication_style",
    "humor_level",
    "values",
}


@router.get("/personas", response_model=list[PersonaRead])
def list_personas(db: Session = Depends(get_db)) -> list[Persona]:
    return list(db.scalars(select(Persona).order_by(Persona.created_at.desc())))


@router.post("/personas", response_model=PersonaRead, status_code=status.HTTP_201_CREATED)
def create_persona(payload: PersonaCreate, db: Session = Depends(get_db)) -> Persona:
    validate_persona_payload(payload)
    persona = Persona(
        name=payload.name.strip(),
        age=payload.age,
        gender=payload.gender,
        physical_json=payload.physical_json,
        voice_json=payload.voice_json,
        personality_json=payload.personality_json,
        status=Status.draft,
    )
    db.add(persona)
    db.commit()
    db.refresh(persona)
    return persona


@router.get("/personas/{persona_id}", response_model=PersonaRead)
def get_persona(persona_id: int, db: Session = Depends(get_db)) -> Persona:
    persona = db.get(Persona, persona_id)
    if persona is None:
        raise HTTPException(status_code=404, detail="Persona not found.")
    return persona


@router.delete("/personas/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_persona(persona_id: int, db: Session = Depends(get_db)) -> None:
    persona = db.get(Persona, persona_id)
    if persona is None:
        raise HTTPException(status_code=404, detail="Persona not found.")
    db.delete(persona)
    db.commit()


@router.post("/personas/{persona_id}/generate-assets", response_model=PersonaGenerationJobRead)
def generate_persona_assets(
    persona_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> PersonaGenerationJob:
    persona = db.get(Persona, persona_id)
    if persona is None:
        raise HTTPException(status_code=404, detail="Persona not found.")

    persona.status = Status.queued
    persona.error_message = None
    job = PersonaGenerationJob(
        persona_id=persona.id,
        status=Status.queued,
        current_step="Queued",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(run_persona_generation_job, job.id)
    return job


@router.get("/personas/jobs/{job_id}", response_model=PersonaGenerationJobRead)
def get_persona_generation_job(job_id: int, db: Session = Depends(get_db)) -> PersonaGenerationJob:
    job = db.get(PersonaGenerationJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Persona generation job not found.")
    return job


def validate_persona_payload(payload: PersonaCreate) -> None:
    missing_physical = sorted(REQUIRED_PHYSICAL_FIELDS - set(payload.physical_json))
    if missing_physical:
        raise HTTPException(status_code=422, detail=f"Missing physical attributes: {', '.join(missing_physical)}.")

    if not payload.voice_json.get("voice_id"):
        raise HTTPException(status_code=422, detail="A selected ElevenLabs voice_id is required.")

    missing_personality = sorted(REQUIRED_PERSONALITY_FIELDS - set(payload.personality_json))
    if missing_personality:
        raise HTTPException(status_code=422, detail=f"Missing personality attributes: {', '.join(missing_personality)}.")

    values = payload.personality_json.get("values")
    if not isinstance(values, list) or len(values) > 2:
        raise HTTPException(status_code=422, detail="Personality values must be a list with at most 2 entries.")
