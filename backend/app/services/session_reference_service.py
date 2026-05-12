import asyncio
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

        job.current_step = "Generating reference assets"
        db.commit()

        generated_paths = await _generate_reference_assets(
            session=session,
            storage=storage,
            renderer=renderer,
            image_service=image_service,
            context=context,
            persona_reference_path=str(persona_reference_path),
        )
        for field_name, relative_path in generated_paths.items():
            setattr(session, field_name, relative_path)

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


async def _generate_reference_assets(
    *,
    session: AdSession,
    storage: StorageService,
    renderer: PromptRenderer,
    image_service: OpenAIImageService,
    context: dict[str, Any],
    persona_reference_path: str,
) -> dict[str, str]:
    results: dict[str, str] = {}

    async def generate_character_reference() -> None:
        if _stored_file_exists(storage, session.session_character_ref_path):
            return
        prompt = renderer.render_template("session_character_edit.json", context)
        path = storage.session_asset_path(session.id, "session_character_reference.png")
        await image_service.generate_image(prompt, [persona_reference_path], str(path))
        results["session_character_ref_path"] = storage.relative_path(path)

    async def generate_environment_references() -> None:
        base_path = storage.session_asset_path(session.id, "environment_base.png")
        if not _stored_file_exists(storage, session.environment_base_path):
            base_prompt = renderer.render_template("environment_base.json", context)
            await image_service.generate_image(base_prompt, None, str(base_path))
            results["environment_base_path"] = storage.relative_path(base_path)
        elif session.environment_base_path:
            base_path = storage.path_from_relative(session.environment_base_path)

        if _stored_file_exists(storage, session.environment_ref_path):
            return
        reference_prompt = renderer.render_template("environment_reference.json", context)
        reference_path = storage.session_asset_path(session.id, "environment_reference.png")
        await image_service.generate_image(reference_prompt, [str(base_path)], str(reference_path))
        results["environment_ref_path"] = storage.relative_path(reference_path)

    async def generate_product_reference() -> None:
        if _stored_file_exists(storage, session.product_ref_path):
            return
        prompt = renderer.render_template("product_reference.json", context)
        input_paths = [str(storage.path_from_relative(path)) for path in session.product_upload_paths_json]
        path = storage.session_asset_path(session.id, "product_reference.png")
        await image_service.generate_image(prompt, input_paths, str(path))
        results["product_ref_path"] = storage.relative_path(path)

    await asyncio.gather(
        generate_character_reference(),
        generate_environment_references(),
        generate_product_reference(),
    )
    return results


def _stored_file_exists(storage: StorageService, relative_path: str | None) -> bool:
    if not relative_path:
        return False
    return storage.path_from_relative(relative_path).is_file()
