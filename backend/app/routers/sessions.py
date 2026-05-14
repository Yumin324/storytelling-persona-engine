from dataclasses import asdict

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import ProviderError
from app.models import AdSession, Persona, SessionReferenceJob, Status
from app.schemas import AdSessionCreate, AdSessionRead, AdSessionUpdate, ScriptUpdate, SessionReferenceJobRead
from app.services.compliance_service import ComplianceService
from app.services.session_reference_service import run_session_reference_job
from app.services.script_generation_service import generate_compliant_script
from app.services.storage_service import StorageService

router = APIRouter()

ALLOWED_IMAGE_TYPES = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024


@router.post("/sessions", response_model=AdSessionRead, status_code=status.HTTP_201_CREATED)
def create_session(payload: AdSessionCreate, db: Session = Depends(get_db)) -> AdSession:
    persona = db.get(Persona, payload.persona_id)
    if persona is None:
        raise HTTPException(status_code=404, detail="Persona not found.")

    session = AdSession(
        persona_id=payload.persona_id,
        outfit=payload.outfit,
        accessories_json=payload.accessories_json,
        environment_json=payload.environment_json,
        product_json=payload.product_json,
        product_upload_paths_json=payload.product_upload_paths_json,
        script_json=payload.script_json,
        status=Status.draft,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/sessions", response_model=list[AdSessionRead])
def list_sessions(db: Session = Depends(get_db)) -> list[AdSession]:
    return list(db.scalars(select(AdSession).order_by(AdSession.updated_at.desc())))


@router.get("/sessions/{session_id}", response_model=AdSessionRead)
def get_session(session_id: int, db: Session = Depends(get_db)) -> AdSession:
    session = db.get(AdSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return session


@router.put("/sessions/{session_id}", response_model=AdSessionRead)
def update_session(session_id: int, payload: AdSessionUpdate, db: Session = Depends(get_db)) -> AdSession:
    session = db.get(AdSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    updates = payload.model_dump(exclude_unset=True)
    if "persona_id" in updates and db.get(Persona, updates["persona_id"]) is None:
        raise HTTPException(status_code=404, detail="Persona not found.")

    invalidate_stale_references(session, updates)

    for key, value in updates.items():
        setattr(session, key, value)

    if session.status == Status.completed:
        session.status = Status.draft
    session.error_message = None
    db.commit()
    db.refresh(session)
    return session


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: int, db: Session = Depends(get_db)) -> None:
    session = db.get(AdSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    db.delete(session)
    db.commit()


@router.post("/sessions/{session_id}/upload-product-images", response_model=AdSessionRead)
async def upload_product_images(
    session_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
) -> AdSession:
    session = db.get(AdSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    if not files:
        raise HTTPException(status_code=422, detail="At least one product image is required.")

    storage = StorageService()
    existing_paths = list(session.product_upload_paths_json or [])
    saved_paths: list[str] = []

    for index, upload in enumerate(files, start=len(existing_paths) + 1):
        extension = ALLOWED_IMAGE_TYPES.get(upload.content_type or "")
        if extension is None:
            raise HTTPException(status_code=422, detail="Only PNG, JPG, and WEBP product images are supported.")

        content = await upload.read()
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Product image upload exceeds the 8 MB limit.")

        path = storage.session_upload_path(session.id, f"product_{index:03d}{extension}")
        path.write_bytes(content)
        saved_paths.append(storage.relative_path(path))

    session.product_upload_paths_json = existing_paths + saved_paths
    clear_stored_asset(storage, session.product_ref_path)
    session.product_ref_path = None
    session.status = Status.draft
    session.error_message = None
    db.commit()
    db.refresh(session)
    return session


@router.delete("/sessions/{session_id}/product-images", response_model=AdSessionRead)
def remove_product_image(
    session_id: int,
    image_path: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> AdSession:
    session = db.get(AdSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    existing_paths = list(session.product_upload_paths_json or [])
    if image_path not in existing_paths:
        raise HTTPException(status_code=404, detail="Product image not found on this session.")

    storage = StorageService()
    try:
        stored_path = storage.path_from_relative(image_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid product image path.") from exc

    if stored_path.is_file():
        stored_path.unlink()

    session.product_upload_paths_json = [path for path in existing_paths if path != image_path]
    clear_stored_asset(storage, session.product_ref_path)
    session.product_ref_path = None
    session.status = Status.draft
    session.error_message = None
    db.commit()
    db.refresh(session)
    return session


@router.post("/sessions/{session_id}/generate-references", response_model=SessionReferenceJobRead)
def generate_references(
    session_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> SessionReferenceJob:
    session = db.get(AdSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    validate_session_ready(session, db)

    session.status = Status.queued
    session.error_message = None
    job = SessionReferenceJob(session_id=session.id, status=Status.queued, current_step="Queued")
    db.add(job)
    db.commit()
    db.refresh(job)
    background_tasks.add_task(run_session_reference_job, job.id)
    return job


@router.get("/sessions/{session_id}/reference-job/{job_id}", response_model=SessionReferenceJobRead)
def get_reference_job(session_id: int, job_id: int, db: Session = Depends(get_db)) -> SessionReferenceJob:
    job = db.get(SessionReferenceJob, job_id)
    if job is None or job.session_id != session_id:
        raise HTTPException(status_code=404, detail="Reference generation job not found.")
    return job


@router.post("/sessions/{session_id}/generate-script", response_model=AdSessionRead)
async def generate_script(session_id: int, db: Session = Depends(get_db)) -> AdSession:
    session = db.get(AdSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    try:
        script = await generate_compliant_script(db, session)
    except ProviderError as exc:
        session.error_message = exc.message
        db.commit()
        raise HTTPException(status_code=503, detail=asdict(exc.normalized())) from exc
    session.script_json = script
    session.error_message = None
    db.commit()
    db.refresh(session)
    return session


@router.put("/sessions/{session_id}/script", response_model=AdSessionRead)
def update_script(session_id: int, payload: ScriptUpdate, db: Session = Depends(get_db)) -> AdSession:
    session = db.get(AdSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    expected_scene_count = int((session.product_json or {}).get("number_of_scenes") or 0)
    errors = ComplianceService().validate_script(payload.script_json, expected_scene_count)
    if errors:
        raise HTTPException(
            status_code=422,
            detail={"message": "Edited script failed compliance validation.", "errors": errors},
        )

    session.script_json = payload.script_json
    session.error_message = None
    db.commit()
    db.refresh(session)
    return session


def invalidate_stale_references(session: AdSession, updates: dict) -> None:
    storage = StorageService()

    if any(field_changed(session, updates, field) for field in ("persona_id", "outfit", "accessories_json")):
        clear_stored_asset(storage, session.session_character_ref_path)
        session.session_character_ref_path = None

    if field_changed(session, updates, "environment_json"):
        clear_stored_asset(storage, session.environment_base_path)
        clear_stored_asset(storage, session.environment_ref_path)
        session.environment_base_path = None
        session.environment_ref_path = None

    if any(field_changed(session, updates, field) for field in ("product_json", "product_upload_paths_json")):
        clear_stored_asset(storage, session.product_ref_path)
        session.product_ref_path = None


def field_changed(session: AdSession, updates: dict, field_name: str) -> bool:
    return field_name in updates and getattr(session, field_name) != updates[field_name]


def clear_stored_asset(storage: StorageService, relative_path: str | None) -> None:
    if not relative_path:
        return
    try:
        path = storage.path_from_relative(relative_path)
    except ValueError:
        return
    if path.is_file():
        path.unlink()


def validate_session_ready(session: AdSession, db: Session) -> None:
    persona = db.get(Persona, session.persona_id)
    if persona is None:
        raise HTTPException(status_code=404, detail="Persona not found.")
    if persona.status != Status.completed or not persona.reference_sheet_path:
        raise HTTPException(status_code=422, detail="Selected persona must have completed reference assets.")
    if not session.product_json.get("name"):
        raise HTTPException(status_code=422, detail="Product name is required.")
    if not session.product_json.get("key_benefits"):
        raise HTTPException(status_code=422, detail="Key benefits are required.")
    if not session.product_json.get("target_audience"):
        raise HTTPException(status_code=422, detail="Target audience is required.")
    scene_count = int(session.product_json.get("number_of_scenes") or 0)
    if scene_count < 3 or scene_count > 10:
        raise HTTPException(status_code=422, detail="Number of scenes must be between 3 and 10.")
    if not session.product_upload_paths_json:
        raise HTTPException(status_code=422, detail="Upload at least one product image.")
    if not session.product_json.get("cta"):
        raise HTTPException(status_code=422, detail="Call to action is required.")
