from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.errors import ProviderError
from app.models import Persona, PersonaGenerationJob, Status
from app.services.openai_image_service import OpenAIImageService
from app.services.prompt_renderer import PromptRenderer
from app.services.storage_service import StorageService


def build_persona_prompt_context(persona: Persona) -> dict[str, Any]:
    return {
        "persona": {
            "id": persona.id,
            "name": persona.name,
            "age": persona.age,
            "gender": persona.gender,
            "physical": persona.physical_json,
            "voice": persona.voice_json,
            "personality": persona.personality_json,
        },
        "session": {},
        "environment": {},
        "product": {},
        "scene": {},
        "meta": {"timestamp": datetime.now(timezone.utc).isoformat()},
    }


async def run_persona_generation_job(job_id: int) -> None:
    db = SessionLocal()
    try:
        await _run_persona_generation_job(db, job_id)
    finally:
        db.close()


async def _run_persona_generation_job(db: Session, job_id: int) -> None:
    job = db.get(PersonaGenerationJob, job_id)
    if job is None:
        return

    persona = db.get(Persona, job.persona_id)
    if persona is None:
        job.status = Status.failed
        job.error_message = "Persona was deleted before generation started."
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        return

    renderer = PromptRenderer()
    storage = StorageService()
    image_service = OpenAIImageService()

    try:
        job.status = Status.running
        job.current_step = "Rendering character base prompt"
        job.started_at = datetime.now(timezone.utc)
        persona.status = Status.running
        persona.error_message = None
        db.commit()

        context = build_persona_prompt_context(persona)
        base_prompt = renderer.render_template("character_base.json", context)
        base_path = storage.persona_asset_path(persona.id, "base.png")

        job.current_step = "Generating base avatar"
        db.commit()
        await image_service.generate_image(base_prompt, None, str(base_path), db=db)
        persona.base_image_path = storage.relative_path(base_path)
        db.commit()

        reference_prompt = renderer.render_template("character_reference.json", context)
        reference_path = storage.persona_asset_path(persona.id, "reference_sheet.png")

        job.current_step = "Generating character reference sheet"
        db.commit()
        await image_service.generate_image(reference_prompt, [str(base_path)], str(reference_path), db=db)

        persona.reference_sheet_path = storage.relative_path(reference_path)
        persona.status = Status.completed
        persona.error_message = None
        job.status = Status.completed
        job.current_step = "Completed"
        job.error_message = None
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:
        message = exc.message if isinstance(exc, ProviderError) else str(exc)
        persona.status = Status.failed
        persona.error_message = message
        job.status = Status.failed
        job.error_message = message
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
