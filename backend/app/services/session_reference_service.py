from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.errors import ProviderError
from app.models import AdSession, Persona, SessionReferenceJob, Status
from app.services.openai_image_service import OpenAIImageService
from app.services.prompt_renderer import PromptRenderer
from app.services.storage_service import StorageService


def build_session_prompt_context(session: AdSession, persona: Persona) -> dict[str, Any]:
    return {
        "persona": {
            "id": persona.id,
            "name": persona.name,
            "age": persona.age,
            "gender": persona.gender,
            "physical": persona.physical_json,
            "voice": persona.voice_json,
            "personality": persona.personality_json,
            "summary": f"{persona.name} - {persona.personality_json.get('content_niche', '')}",
        },
        "session": {
            "id": session.id,
            "outfit": session.outfit or "",
            "accessories": session.accessories_json,
        },
        "environment": session.environment_json,
        "product": session.product_json,
        "script": session.script_json or {},
        "scene": {},
        "meta": {"timestamp": datetime.now(timezone.utc).isoformat()},
    }


async def run_session_reference_job(job_id: int) -> None:
    db = SessionLocal()
    try:
        await _run_session_reference_job(db, job_id)
    finally:
        db.close()


async def _run_session_reference_job(db: Session, job_id: int) -> None:
    job = db.get(SessionReferenceJob, job_id)
    if job is None:
        return

    session = db.get(AdSession, job.session_id)
    if session is None:
        job.status = Status.failed
        job.error_message = "Session was deleted before reference generation started."
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        return

    persona = db.get(Persona, session.persona_id)
    renderer = PromptRenderer()
    storage = StorageService()
    image_service = OpenAIImageService()

    try:
        if persona is None:
            raise ValueError("Selected persona no longer exists.")
        if persona.status != Status.completed or not persona.reference_sheet_path:
            raise ValueError("Selected persona must have a completed character reference sheet.")
        if not session.product_upload_paths_json:
            raise ValueError("Upload at least one product image before generating references.")

        job.status = Status.running
        job.current_step = "Rendering reference prompts"
        job.started_at = datetime.now(timezone.utc)
        session.status = Status.running
        session.error_message = None
        db.commit()

        context = build_session_prompt_context(session, persona)
        persona_reference_path = storage.path_from_relative(persona.reference_sheet_path)

        job.current_step = "Generating session character reference"
        db.commit()
        session_character_prompt = renderer.render_template("session_character_edit.json", context)
        session_character_path = storage.session_asset_path(session.id, "session_character_reference.png")
        await image_service.generate_image(
            session_character_prompt,
            [str(persona_reference_path)],
            str(session_character_path),
            db=db,
        )
        session.session_character_ref_path = storage.relative_path(session_character_path)
        db.commit()

        job.current_step = "Generating environment base image"
        db.commit()
        environment_base_prompt = renderer.render_template("environment_base.json", context)
        environment_base_path = storage.session_asset_path(session.id, "environment_base.png")
        await image_service.generate_image(environment_base_prompt, None, str(environment_base_path), db=db)
        session.environment_base_path = storage.relative_path(environment_base_path)
        db.commit()

        job.current_step = "Generating environment reference sheet"
        db.commit()
        environment_reference_prompt = renderer.render_template("environment_reference.json", context)
        environment_reference_path = storage.session_asset_path(session.id, "environment_reference.png")
        await image_service.generate_image(
            environment_reference_prompt,
            [str(environment_base_path)],
            str(environment_reference_path),
            db=db,
        )
        session.environment_ref_path = storage.relative_path(environment_reference_path)
        db.commit()

        job.current_step = "Generating product reference sheet"
        db.commit()
        product_reference_prompt = renderer.render_template("product_reference.json", context)
        product_input_paths = [str(storage.path_from_relative(path)) for path in session.product_upload_paths_json]
        product_reference_path = storage.session_asset_path(session.id, "product_reference.png")
        await image_service.generate_image(
            product_reference_prompt,
            product_input_paths,
            str(product_reference_path),
            db=db,
        )
        session.product_ref_path = storage.relative_path(product_reference_path)

        session.status = Status.completed
        session.error_message = None
        job.status = Status.completed
        job.current_step = "Completed"
        job.error_message = None
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:
        message = exc.message if isinstance(exc, ProviderError) else str(exc)
        session.status = Status.failed
        session.error_message = message
        job.status = Status.failed
        job.error_message = message
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
