from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.errors import ProviderError
from app.models import AdSession, Persona, ProductionJob, Scene, Status
from app.services.compliance_service import ComplianceService
from app.services.openai_llm_service import OpenAILLMService
from app.services.prompt_renderer import PromptRenderer


async def run_production_prompt_job(job_id: int) -> None:
    db = SessionLocal()
    try:
        await _run_production_prompt_job(db, job_id)
    finally:
        db.close()


async def _run_production_prompt_job(db: Session, job_id: int) -> None:
    job = db.get(ProductionJob, job_id)
    if job is None:
        return

    session = db.get(AdSession, job.session_id)
    if session is None:
        job.status = Status.failed
        job.error_message = "Session was deleted before production prompt generation started."
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        return

    persona = db.get(Persona, session.persona_id)
    scenes = list(db.scalars(select(Scene).where(Scene.job_id == job.id).order_by(Scene.scene_number)))
    renderer = PromptRenderer()
    llm = OpenAILLMService()
    compliance = ComplianceService()
    completed = 0
    failed = 0
    product_revealed = False

    job.status = Status.running
    job.current_step = "Generating scene prompts"
    job.started_at = datetime.now(timezone.utc)
    db.commit()

    for scene in scenes:
        scene.status = Status.running
        job.current_step = f"Generating prompts for Scene {scene.scene_number:02d}"
        db.commit()

        try:
            product_revealed = product_revealed or is_product_revealed(session, scene)
            context = build_scene_prompt_context(session, persona, scene, product_revealed)
            prompt = renderer.render_template("scene_prompt_writer.md", context)
            output = await llm.generate_scene_prompts(prompt, db=db)
            errors = compliance.validate_scene_prompt_output(output)
            if errors:
                raise ValueError("; ".join(errors))

            scene.image_prompt = output["image_prompt"]
            scene.video_prompt = output["video_prompt"]
            scene.voice_prompt = output["voice_prompt"]
            scene.safety_notes_json = output.get("safety_notes") or []
            scene.status = Status.completed
            scene.error_message = None
            completed += 1
        except Exception as exc:
            message = exc.message if isinstance(exc, ProviderError) else str(exc)
            scene.status = Status.failed
            scene.error_message = message
            failed += 1

        total = max(len(scenes), 1)
        job.progress_percent = int((completed / total) * 100)
        db.commit()

    job.completed_at = datetime.now(timezone.utc)
    if failed:
        job.status = Status.failed
        job.error_message = f"{failed} scene prompt generation step(s) failed."
    else:
        job.status = Status.completed
        job.progress_percent = 100
        job.error_message = None
    job.current_step = "Completed" if job.status == Status.completed else "Failed"
    db.commit()


def build_scene_prompt_context(
    session: AdSession,
    persona: Persona | None,
    scene: Scene,
    product_revealed: bool,
) -> dict[str, Any]:
    product = session.product_json or {}
    persona_payload = {
        "id": persona.id if persona else None,
        "name": persona.name if persona else "Selected persona",
        "age": persona.age if persona else "",
        "gender": persona.gender if persona else "",
        "physical": persona.physical_json if persona else {},
        "voice": persona.voice_json if persona else {},
        "personality": persona.personality_json if persona else {},
        "summary": (session.script_json or {}).get("persona_summary", ""),
    }

    return {
        "persona": persona_payload,
        "session": {
            "id": session.id,
            "outfit": session.outfit or "",
            "accessories": session.accessories_json,
            "session_character_ref_path": session.session_character_ref_path,
            "environment_ref_path": session.environment_ref_path,
            "product_ref_path": session.product_ref_path if product_revealed else None,
        },
        "environment": session.environment_json or {},
        "product": product,
        "script": session.script_json or {},
        "scene": {
            "scene_id": f"Scene {scene.scene_number:02d}",
            "visual": scene.script_visual,
            "voiceover": scene.script_voiceover,
            "product_revealed": product_revealed,
        },
        "meta": {"timestamp": datetime.now(timezone.utc).isoformat()},
    }


def is_product_revealed(session: AdSession, scene: Scene) -> bool:
    product_name = str((session.product_json or {}).get("name") or "").casefold()
    scene_text = f"{scene.script_visual} {scene.script_voiceover}".casefold()
    if product_name and product_name in scene_text:
        return True
    return scene.scene_number >= 3
