from pathlib import Path

from app.config import Settings, get_settings


class StorageService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.root = Path(self.settings.storage_root).resolve()

    def ensure_base_directories(self) -> None:
        for directory in (
            self.root,
            self.root / "personas",
            self.root / "sessions",
            self.root / "jobs",
            self.root / "uploads",
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def persona_dir(self, persona_id: int) -> Path:
        return self._ensure_id_dir("personas", persona_id)

    def session_dir(self, session_id: int) -> Path:
        return self._ensure_id_dir("sessions", session_id)

    def session_uploads_dir(self, session_id: int) -> Path:
        path = self.session_dir(session_id) / "uploads"
        path.mkdir(parents=True, exist_ok=True)
        return self._safe_path(path)

    def job_dir(self, job_id: int) -> Path:
        return self._ensure_id_dir("jobs", job_id)

    def scene_dir(self, job_id: int, scene_number: int) -> Path:
        self._validate_positive_int(scene_number, "scene_number")
        path = self.job_dir(job_id) / f"scene_{scene_number:02d}"
        path.mkdir(parents=True, exist_ok=True)
        return self._safe_path(path)

    def persona_asset_path(self, persona_id: int, filename: str) -> Path:
        return self._asset_path(self.persona_dir(persona_id), filename)

    def session_asset_path(self, session_id: int, filename: str) -> Path:
        return self._asset_path(self.session_dir(session_id), filename)

    def scene_asset_path(self, job_id: int, scene_number: int, filename: str) -> Path:
        return self._asset_path(self.scene_dir(job_id, scene_number), filename)

    def relative_path(self, path: Path) -> str:
        safe_path = self._safe_path(path)
        return safe_path.relative_to(self.root).as_posix()

    def _ensure_id_dir(self, category: str, entity_id: int) -> Path:
        self._validate_positive_int(entity_id, f"{category}_id")
        path = self.root / category / str(entity_id)
        path.mkdir(parents=True, exist_ok=True)
        return self._safe_path(path)

    def _asset_path(self, base_dir: Path, filename: str) -> Path:
        if Path(filename).name != filename:
            raise ValueError("filename must not include path separators")
        if filename in {"", ".", ".."}:
            raise ValueError("filename is invalid")
        return self._safe_path(base_dir / filename)

    def _safe_path(self, path: Path) -> Path:
        resolved = path.resolve()
        if resolved != self.root and self.root not in resolved.parents:
            raise ValueError("resolved path escapes storage root")
        return resolved

    @staticmethod
    def _validate_positive_int(value: int, name: str) -> None:
        if not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be a positive integer")
