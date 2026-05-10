from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Status(StrEnum):
    draft = "draft"
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    retrying = "retrying"
    cancelled = "cancelled"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class Persona(TimestampMixin, Base):
    __tablename__ = "personas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[str] = mapped_column(String(40), nullable=False)
    physical_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    voice_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    personality_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    base_image_path: Mapped[str | None] = mapped_column(String(500))
    reference_sheet_path: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[Status] = mapped_column(Enum(Status), default=Status.draft, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)

    ad_sessions: Mapped[list["AdSession"]] = relationship(back_populates="persona")
    generation_jobs: Mapped[list["PersonaGenerationJob"]] = relationship(
        back_populates="persona",
        cascade="all, delete-orphan",
    )


class PersonaGenerationJob(TimestampMixin, Base):
    __tablename__ = "persona_generation_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    persona_id: Mapped[int] = mapped_column(ForeignKey("personas.id"), nullable=False, index=True)
    status: Mapped[Status] = mapped_column(Enum(Status), default=Status.queued, nullable=False)
    current_step: Mapped[str | None] = mapped_column(String(255))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    persona: Mapped[Persona] = relationship(back_populates="generation_jobs")


class AdSession(TimestampMixin, Base):
    __tablename__ = "ad_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    persona_id: Mapped[int] = mapped_column(ForeignKey("personas.id"), nullable=False, index=True)
    outfit: Mapped[str | None] = mapped_column(String(500))
    accessories_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    environment_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    product_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    product_upload_paths_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    script_json: Mapped[dict | None] = mapped_column(JSON)
    session_character_ref_path: Mapped[str | None] = mapped_column(String(500))
    environment_base_path: Mapped[str | None] = mapped_column(String(500))
    environment_ref_path: Mapped[str | None] = mapped_column(String(500))
    product_ref_path: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[Status] = mapped_column(Enum(Status), default=Status.draft, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)

    persona: Mapped[Persona] = relationship(back_populates="ad_sessions")
    production_jobs: Mapped[list["ProductionJob"]] = relationship(back_populates="session")
    scenes: Mapped[list["Scene"]] = relationship(back_populates="session")


class ProductionJob(TimestampMixin, Base):
    __tablename__ = "production_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("ad_sessions.id"), nullable=False, index=True)
    status: Mapped[Status] = mapped_column(Enum(Status), default=Status.queued, nullable=False)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_step: Mapped[str | None] = mapped_column(String(255))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    session: Mapped[AdSession] = relationship(back_populates="production_jobs")
    scenes: Mapped[list["Scene"]] = relationship(back_populates="job")


class Scene(TimestampMixin, Base):
    __tablename__ = "scenes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("ad_sessions.id"), nullable=False, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("production_jobs.id"), nullable=False, index=True)
    scene_number: Mapped[int] = mapped_column(Integer, nullable=False)
    script_visual: Mapped[str] = mapped_column(Text, nullable=False)
    script_voiceover: Mapped[str] = mapped_column(Text, nullable=False)
    image_prompt: Mapped[str | None] = mapped_column(Text)
    video_prompt: Mapped[str | None] = mapped_column(Text)
    voice_prompt: Mapped[str | None] = mapped_column(Text)
    first_frame_path: Mapped[str | None] = mapped_column(String(500))
    video_path: Mapped[str | None] = mapped_column(String(500))
    voice_path: Mapped[str | None] = mapped_column(String(500))
    zip_path: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[Status] = mapped_column(Enum(Status), default=Status.draft, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)

    session: Mapped[AdSession] = relationship(back_populates="scenes")
    job: Mapped[ProductionJob] = relationship(back_populates="scenes")


class ApiLog(Base):
    __tablename__ = "api_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    provider: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(120), nullable=False)
    related_type: Mapped[str | None] = mapped_column(String(80), index=True)
    related_id: Mapped[int | None] = mapped_column(Integer, index=True)
    request_summary_json: Mapped[dict | None] = mapped_column(JSON)
    response_summary_json: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[Status] = mapped_column(Enum(Status), nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
