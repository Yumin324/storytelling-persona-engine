from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import Status


JsonDict = dict[str, Any]


class TimestampedResponse(BaseModel):
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PersonaBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    age: int = Field(ge=18, le=70)
    gender: str
    physical_json: JsonDict = Field(default_factory=dict)
    voice_json: JsonDict = Field(default_factory=dict)
    personality_json: JsonDict = Field(default_factory=dict)

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, value: str) -> str:
        normalized = value.strip()
        if normalized not in {"Male", "Female"}:
            raise ValueError("gender must be Male or Female")
        return normalized


class PersonaCreate(PersonaBase):
    pass


class PersonaUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    age: int | None = Field(default=None, ge=18, le=70)
    gender: str | None = None
    physical_json: JsonDict | None = None
    voice_json: JsonDict | None = None
    personality_json: JsonDict | None = None
    status: Status | None = None
    error_message: str | None = None


class PersonaRead(PersonaBase, TimestampedResponse):
    id: int
    base_image_path: str | None
    reference_sheet_path: str | None
    status: Status
    error_message: str | None


class PersonaGenerationJobRead(TimestampedResponse):
    id: int
    persona_id: int
    status: Status
    current_step: str | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None


class AdSessionBase(BaseModel):
    persona_id: int
    outfit: str | None = None
    accessories_json: list[Any] = Field(default_factory=list)
    environment_json: JsonDict = Field(default_factory=dict)
    product_json: JsonDict = Field(default_factory=dict)
    product_upload_paths_json: list[str] = Field(default_factory=list)
    script_json: JsonDict | None = None


class AdSessionCreate(AdSessionBase):
    pass


class AdSessionUpdate(BaseModel):
    persona_id: int | None = None
    outfit: str | None = None
    accessories_json: list[Any] | None = None
    environment_json: JsonDict | None = None
    product_json: JsonDict | None = None
    product_upload_paths_json: list[str] | None = None
    script_json: JsonDict | None = None
    status: Status | None = None
    error_message: str | None = None


class AdSessionRead(AdSessionBase, TimestampedResponse):
    id: int
    session_character_ref_path: str | None
    environment_base_path: str | None
    environment_ref_path: str | None
    product_ref_path: str | None
    status: Status
    error_message: str | None


class ScriptUpdate(BaseModel):
    script_json: JsonDict


class SessionReferenceJobRead(TimestampedResponse):
    id: int
    session_id: int
    status: Status
    current_step: str | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None


class ProductionJobBase(BaseModel):
    session_id: int


class ProductionJobCreate(ProductionJobBase):
    pass


class ProductionJobUpdate(BaseModel):
    status: Status | None = None
    progress_percent: int | None = Field(default=None, ge=0, le=100)
    current_step: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class ProductionJobRead(ProductionJobBase, TimestampedResponse):
    id: int
    status: Status
    progress_percent: int
    current_step: str | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None


class SceneBase(BaseModel):
    session_id: int
    job_id: int
    scene_number: int = Field(ge=1)
    script_visual: str = Field(min_length=1)
    script_voiceover: str = Field(min_length=1)


class SceneCreate(SceneBase):
    pass


class SceneUpdate(BaseModel):
    script_visual: str | None = Field(default=None, min_length=1)
    script_voiceover: str | None = Field(default=None, min_length=1)
    image_prompt: str | None = None
    video_prompt: str | None = None
    voice_prompt: str | None = None
    first_frame_path: str | None = None
    video_path: str | None = None
    voice_path: str | None = None
    zip_path: str | None = None
    status: Status | None = None
    error_message: str | None = None


class SceneRead(SceneBase, TimestampedResponse):
    id: int
    image_prompt: str | None
    video_prompt: str | None
    voice_prompt: str | None
    first_frame_path: str | None
    video_path: str | None
    voice_path: str | None
    zip_path: str | None
    status: Status
    error_message: str | None


class ApiLogCreate(BaseModel):
    provider: str
    operation: str
    related_type: str | None = None
    related_id: int | None = None
    request_summary_json: JsonDict | None = None
    response_summary_json: JsonDict | None = None
    status: Status
    status_code: int | None = None
    duration_ms: int | None = None
    error_message: str | None = None


class ApiLogRead(ApiLogCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
