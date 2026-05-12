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
    base_image_path: Mapped[str] = mapped_column(String(500), nullable=True)
    reference_sheet_path: Mapped[str] = mapped_column(String(500), nullable=True)
    status: Mapped[Status] = mapped_column(Enum(Status), default=Status.draft, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    ad_sessions: Mapped[list["AdSession"]] = relationship(back_populates="persona", cascade="all, delete-orphan")
    generation_jobs: Mapped[list["PersonaGenerationJob"]] = relationship(
        back_populates="persona",
        cascade="all, delete-orphan",
    )


class PersonaGenerationJob(TimestampMixin, Base):
    __tablename__ = "persona_generation_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    persona_id: Mapped[int] = mapped_column(ForeignKey("personas.id"), nullable=False, index=True)
    status: Mapped[Status] = mapped_column(Enum(Status), default=Status.queued, nullable=False)
    current_step: Mapped[str] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    persona: Mapped[Persona] = relationship(back_populates="generation_jobs")


class AdSession(TimestampMixin, Base):
    __tablename__ = "ad_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    persona_id: Mapped[int] = mapped_column(ForeignKey("personas.id"), nullable=False, index=True)
    outfit: Mapped[str] = mapped_column(String(500), nullable=True)
    accessories_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    environment_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    product_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    product_upload_paths_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    script_json: Mapped[dict] = mapped_column(JSON, nullable=True)
    session_character_ref_path: Mapped[str] = mapped_column(String(500), nullable=True)
    environment_base_path: Mapped[str] = mapped_column(String(500), nullable=True)
    environment_ref_path: Mapped[str] = mapped_column(String(500), nullable=True)
    product_ref_path: Mapped[str] = mapped_column(String(500), nullable=True)
    status: Mapped[Status] = mapped_column(Enum(Status), default=Status.draft, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    persona: Mapped[Persona] = relationship(back_populates="ad_sessions")
    reference_jobs: Mapped[list["SessionReferenceJob"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )
    production_jobs: Mapped[list["ProductionJob"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )
    scenes: Mapped[list["Scene"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class SessionReferenceJob(TimestampMixin, Base):
    __tablename__ = "session_reference_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("ad_sessions.id"), nullable=False, index=True)
    status: Mapped[Status] = mapped_column(Enum(Status), default=Status.queued, nullable=False)
    current_step: Mapped[str] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped[AdSession] = relationship(back_populates="reference_jobs")


class ProductionJob(TimestampMixin, Base):
    __tablename__ = "production_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("ad_sessions.id"), nullable=False, index=True)
    status: Mapped[Status] = mapped_column(Enum(Status), default=Status.queued, nullable=False)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_step: Mapped[str] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped[AdSession] = relationship(back_populates="production_jobs")
    scenes: Mapped[list["Scene"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class Scene(TimestampMixin, Base):
    __tablename__ = "scenes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("ad_sessions.id"), nullable=False, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("production_jobs.id"), nullable=False, index=True)
    scene_number: Mapped[int] = mapped_column(Integer, nullable=False)
    script_visual: Mapped[str] = mapped_column(Text, nullable=False)
    script_voiceover: Mapped[str] = mapped_column(Text, nullable=False)
    image_prompt: Mapped[str] = mapped_column(Text, nullable=True)
    video_prompt: Mapped[str] = mapped_column(Text, nullable=True)
    voice_prompt: Mapped[str] = mapped_column(Text, nullable=True)
    safety_notes_json: Mapped[list] = mapped_column(JSON, nullable=True)
    first_frame_path: Mapped[str] = mapped_column(String(500), nullable=True)
    video_path: Mapped[str] = mapped_column(String(500), nullable=True)
    voice_path: Mapped[str] = mapped_column(String(500), nullable=True)
    zip_path: Mapped[str] = mapped_column(String(500), nullable=True)
    status: Mapped[Status] = mapped_column(Enum(Status), default=Status.draft, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    session: Mapped[AdSession] = relationship(back_populates="scenes")
    job: Mapped[ProductionJob] = relationship(back_populates="scenes")


class ApiLog(Base):
    __tablename__ = "api_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    provider: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(120), nullable=False)
    related_type: Mapped[str] = mapped_column(String(80), index=True, nullable=True)
    related_id: Mapped[int] = mapped_column(Integer, index=True, nullable=True)
    request_summary_json: Mapped[dict] = mapped_column(JSON, nullable=True)
    response_summary_json: Mapped[dict] = mapped_column(JSON, nullable=True)
    status: Mapped[Status] = mapped_column(Enum(Status), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
