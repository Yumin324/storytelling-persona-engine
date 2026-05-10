import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from app.models import Scene


class ZipService:
    def create_scene_zip(
        self,
        scene: Scene,
        output_path: Path,
        *,
        first_frame_path: Path,
        video_path: Path,
        voice_path: Path,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        metadata = {
            "scene_id": f"Scene {scene.scene_number:02d}",
            "scene_number": scene.scene_number,
            "script_visual": scene.script_visual,
            "script_voiceover": scene.script_voiceover,
            "image_prompt": scene.image_prompt,
            "video_prompt": scene.video_prompt,
            "voice_prompt": scene.voice_prompt,
            "safety_notes": scene.safety_notes_json or [],
            "first_frame_path": scene.first_frame_path,
            "video_path": scene.video_path,
            "voice_path": scene.voice_path,
        }

        with ZipFile(output_path, "w", compression=ZIP_DEFLATED) as zip_file:
            zip_file.writestr("scene_metadata.json", json.dumps(metadata, indent=2))
            self._write_asset(zip_file, first_frame_path, "first_frame.png")
            self._write_asset(zip_file, video_path, "video.mp4")
            self._write_asset(zip_file, voice_path, "voiceover.mp3")

        return output_path

    @staticmethod
    def _write_asset(zip_file: ZipFile, path_value: Path | None, archive_name: str) -> None:
        if not path_value:
            raise ValueError(f"Cannot create scene zip because {archive_name} is missing.")
        path = Path(path_value)
        if not path.is_file():
            raise ValueError(f"Cannot create scene zip because {archive_name} was not found.")
        zip_file.write(path, archive_name)
