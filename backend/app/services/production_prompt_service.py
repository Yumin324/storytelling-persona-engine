from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.errors import ProviderError
from app.models import AdSession, Persona, ProductionJob, Scene, Status
from app.services.compliance_service import ComplianceService
from app.services.elevenlabs_voice_service import ElevenLabsVoiceService
from app.services.kling_video_service import KlingVideoService
from app.services.openai_image_service import OpenAIImageService
from app.services.openai_llm_service import OpenAILLMService
from app.services.prompt_renderer import PromptRenderer
from app.services.storage_service import StorageService
from app.services.zip_service import ZipService


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
    job.status = Status.running
    job.current_step = "Generating scene assets"
    job.started_at = datetime.now(timezone.utc)
    db.commit()

    product_revealed = False
    for scene in scenes:
        product_revealed = product_revealed or is_product_revealed(session, scene)
        await process_scene_assets(db, job, session, persona, scene, product_revealed)
        update_job_progress(db, job)

    job.completed_at = datetime.now(timezone.utc)
    failed = count_failed_scenes(db, job.id)
    if failed:
        job.status = Status.failed
        job.error_message = f"{failed} scene asset generation step(s) failed."
    else:
        job.status = Status.completed
        job.progress_percent = 100
        job.error_message = None
    job.current_step = "Completed" if job.status == Status.completed else "Failed"
    db.commit()


async def retry_scene_asset_generation(scene_id: int) -> None:
    db = SessionLocal()
    try:
        scene = db.get(Scene, scene_id)
        if scene is None:
            return
        job = db.get(ProductionJob, scene.job_id)
        session = db.get(AdSession, scene.session_id)
        if job is None or session is None:
            return
        persona = db.get(Persona, session.persona_id)

        job.status = Status.running
        job.current_step = f"Retrying Scene {scene.scene_number:02d}"
        job.error_message = None
        db.commit()

        product_revealed = is_product_revealed_by_scene_number(session, scene.scene_number)
        await process_scene_assets(db, job, session, persona, scene, product_revealed)
        update_job_progress(db, job)

        failed = count_failed_scenes(db, job.id)
        pending = count_incomplete_scenes(db, job.id)
        if failed:
            job.status = Status.failed
            job.error_message = f"{failed} scene asset generation step(s) failed."
        elif pending:
            job.status = Status.running
            job.error_message = None
        else:
            job.status = Status.completed
            job.progress_percent = 100
            job.error_message = None
        job.current_step = "Completed" if job.status == Status.completed else "Failed" if failed else "Running"
        job.completed_at = datetime.now(timezone.utc) if job.status in {Status.completed, Status.failed} else None
        db.commit()
    finally:
        db.close()


async def process_scene_assets(
    db: Session,
    job: ProductionJob,
    session: AdSession,
    persona: Persona | None,
    scene: Scene,
    product_revealed: bool,
) -> None:
    scene.status = Status.running
    scene.error_message = None
    db.commit()

    try:
        await ensure_scene_prompts(db, job, session, persona, scene, product_revealed)
        await ensure_first_frame(db, job, session, scene, product_revealed)
        await ensure_video(db, job, scene)
        await ensure_voiceover(db, job, persona, scene)
        await ensure_scene_zip(db, job, scene)
        scene.status = Status.completed
        scene.error_message = None
    except Exception as exc:
        message = exc.message if isinstance(exc, ProviderError) else str(exc)
        scene.status = Status.failed
        scene.error_message = message
    db.commit()


async def ensure_scene_prompts(
    db: Session,
    job: ProductionJob,
    session: AdSession,
    persona: Persona | None,
    scene: Scene,
    product_revealed: bool,
) -> None:
    if scene.image_prompt and scene.video_prompt and scene.voice_prompt:
        return

    job.current_step = f"Generating prompts for Scene {scene.scene_number:02d}"
    db.commit()

    renderer = PromptRenderer()
    llm = OpenAILLMService()
    compliance = ComplianceService()
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
    db.commit()


async def ensure_first_frame(
    db: Session,
    job: ProductionJob,
    session: AdSession,
    scene: Scene,
    product_revealed: bool,
) -> None:
    if scene.first_frame_path:
        return

    job.current_step = f"Generating first frame for Scene {scene.scene_number:02d}"
    db.commit()

    storage = StorageService()
    input_images = [
        str(storage.path_from_relative(session.session_character_ref_path)),
        str(storage.path_from_relative(session.environment_ref_path)),
    ]
    if product_revealed and session.product_ref_path:
        input_images.append(str(storage.path_from_relative(session.product_ref_path)))

    output_path = storage.scene_asset_path(job.id, scene.scene_number, "first_frame.png")
    await OpenAIImageService().generate_image(scene.image_prompt, input_images, str(output_path), db=db)
    scene.first_frame_path = storage.relative_path(output_path)
    db.commit()
    update_job_progress(db, job)


async def ensure_video(db: Session, job: ProductionJob, scene: Scene) -> None:
    if scene.video_path:
        return

    job.current_step = f"Generating silent video for Scene {scene.scene_number:02d}"
    db.commit()

    storage = StorageService()
    if not scene.first_frame_path:
        raise ValueError("First-frame image is required before video generation.")

    first_frame_path = storage.path_from_relative(scene.first_frame_path)
    output_path = storage.scene_asset_path(job.id, scene.scene_number, "video.mp4")
    kling = KlingVideoService()
    task_id = await kling.create_video_task(str(first_frame_path), scene.video_prompt, db=db)
    await kling.poll_video_task(task_id, str(output_path), db=db)
    scene.video_path = storage.relative_path(output_path)
    db.commit()
    update_job_progress(db, job)


async def ensure_voiceover(db: Session, job: ProductionJob, persona: Persona | None, scene: Scene) -> None:
    if scene.voice_path:
        return

    job.current_step = f"Generating voiceover for Scene {scene.scene_number:02d}"
    db.commit()

    voice_id = (persona.voice_json or {}).get("voice_id") if persona else None
    if not voice_id:
        raise ValueError("Selected persona voice_id is required for voiceover generation.")

    storage = StorageService()
    output_path = storage.scene_asset_path(job.id, scene.scene_number, "voiceover.mp3")
    await ElevenLabsVoiceService().text_to_speech(
        voice_id,
        scene.script_voiceover,
        scene.voice_prompt or "",
        str(output_path),
        db=db,
    )
    scene.voice_path = storage.relative_path(output_path)
    db.commit()
    update_job_progress(db, job)


async def ensure_scene_zip(db: Session, job: ProductionJob, scene: Scene) -> None:
    if scene.zip_path:
        return

    job.current_step = f"Creating asset zip for Scene {scene.scene_number:02d}"
    db.commit()

    storage = StorageService()
    zip_path = storage.scene_asset_path(job.id, scene.scene_number, f"scene_{scene.scene_number:02d}_assets.zip")

    if not scene.first_frame_path or not scene.video_path or not scene.voice_path:
        raise ValueError("First frame, video, and voiceover are required before creating scene zip.")
    ZipService().create_scene_zip(
        scene,
        zip_path,
        first_frame_path=storage.path_from_relative(scene.first_frame_path),
        video_path=storage.path_from_relative(scene.video_path),
        voice_path=storage.path_from_relative(scene.voice_path),
    )

    scene.zip_path = storage.relative_path(zip_path)
    db.commit()


def update_job_progress(db: Session, job: ProductionJob) -> None:
    scenes = list(db.scalars(select(Scene).where(Scene.job_id == job.id)))
    total_units = max(len(scenes) * 3, 1)
    completed_units = 0
    for scene in scenes:
        completed_units += 1 if scene.first_frame_path else 0
        completed_units += 1 if scene.video_path else 0
        completed_units += 1 if scene.voice_path else 0
    job.progress_percent = int((completed_units / total_units) * 100)
    db.commit()


def count_failed_scenes(db: Session, job_id: int) -> int:
    return len(list(db.scalars(select(Scene).where(Scene.job_id == job_id, Scene.status == Status.failed))))


def count_incomplete_scenes(db: Session, job_id: int) -> int:
    return len(list(db.scalars(select(Scene).where(Scene.job_id == job_id, Scene.status != Status.completed))))


def is_product_revealed_by_scene_number(session: AdSession, scene_number: int) -> bool:
    scenes = list((session.script_json or {}).get("scenes", []))
    product_name = str((session.product_json or {}).get("name") or "").casefold()
    for index, script_scene in enumerate(scenes, start=1):
        text = f"{script_scene.get('visual', '')} {script_scene.get('voiceover', '')}".casefold()
        if (product_name and product_name in text) or index >= 3:
            return scene_number >= index
    return scene_number >= 3


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
