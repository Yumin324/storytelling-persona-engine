from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.services.storage_service import StorageService

router = APIRouter()


@router.get("/files/{relative_path:path}")
def get_storage_file(relative_path: str) -> FileResponse:
    try:
        path = StorageService().path_from_relative(relative_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid file path.") from exc

    if not path.is_file():
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(path)
