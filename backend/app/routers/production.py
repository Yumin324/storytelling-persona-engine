from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AdSession, ProductionJob, Scene, Status
from app.schemas import ProductionJobRead, SceneRead
from app.services.compliance_service import ComplianceService
from app.services.production_prompt_service import retry_scene_asset_generation, run_production_prompt_job
from app.services.storage_service import StorageService

router = APIRouter()


@router.post("/production/{session_id}/start", response_model=ProductionJobRead, status_code=status.HTTP_201_CREATED)
def start_production(
    session_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> ProductionJob:
    session = db.get(AdSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    validate_production_session(session)

    job = ProductionJob(session_id=session.id, status=Status.queued, progress_percent=0, current_step="Queued")
    db.add(job)
    db.flush()

    scenes = session.script_json.get("scenes", [])
    for index, script_scene in enumerate(scenes, start=1):
        db.add(
            Scene(
                session_id=session.id,
                job_id=job.id,
                scene_number=index,
                script_visual=script_scene["visual"],
                script_voiceover=script_scene["voiceover"],
                status=Status.queued,
            )
        )

    db.commit()
    db.refresh(job)
    background_tasks.add_task(run_production_prompt_job, job.id)
    return job


@router.get("/production/jobs/{job_id}", response_model=ProductionJobRead)
def get_production_job(job_id: int, db: Session = Depends(get_db)) -> ProductionJob:
    job = db.get(ProductionJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Production job not found.")
    return job


@router.get("/production/jobs/{job_id}/scenes", response_model=list[SceneRead])
def get_production_job_scenes(job_id: int, db: Session = Depends(get_db)) -> list[Scene]:
    job = db.get(ProductionJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Production job not found.")
    return list(db.scalars(select(Scene).where(Scene.job_id == job_id).order_by(Scene.scene_number)))


@router.post("/production/scenes/{scene_id}/retry", response_model=SceneRead)
def retry_scene(scene_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> Scene:
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="Scene not found.")

    scene.status = Status.retrying
    scene.error_message = None
    job = db.get(ProductionJob, scene.job_id)
    if job is not None:
        job.status = Status.running
        job.current_step = f"Retrying Scene {scene.scene_number:02d}"
        job.error_message = None
    db.commit()
    db.refresh(scene)
    background_tasks.add_task(retry_scene_asset_generation, scene.id)
    return scene


@router.get("/production/scenes/{scene_id}/download")
def download_scene(scene_id: int, db: Session = Depends(get_db)) -> FileResponse:
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="Scene not found.")
    if not scene.zip_path:
        raise HTTPException(status_code=404, detail="Scene ZIP is not available yet.")

    try:
        path = StorageService().path_from_relative(scene.zip_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid scene ZIP path.") from exc

    if not path.is_file():
        raise HTTPException(status_code=404, detail="Scene ZIP file was not found.")
    return FileResponse(path, filename=f"scene_{scene.scene_number:02d}_assets.zip", media_type="application/zip")


def validate_production_session(session: AdSession) -> None:
    script = session.script_json
    if not script:
        raise HTTPException(status_code=422, detail="Session must have an approved script before production starts.")

    expected_scene_count = int((session.product_json or {}).get("number_of_scenes") or 0)
    script_errors = ComplianceService().validate_script(script, expected_scene_count)
    if script_errors:
        raise HTTPException(
            status_code=422,
            detail={"message": "Session script failed compliance validation.", "errors": script_errors},
        )

    missing_refs = [
        label
        for label, path in (
            ("session character reference", session.session_character_ref_path),
            ("environment reference", session.environment_ref_path),
            ("product reference", session.product_ref_path),
        )
        if not path
    ]
    if missing_refs:
        raise HTTPException(status_code=422, detail=f"Missing generated references: {', '.join(missing_refs)}.")
