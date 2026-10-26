import time
from uuid import uuid4

from sqlalchemy import JSON, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SearchRun(Base):
    __tablename__ = "search_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    status: Mapped[str] = mapped_column(String(20), default="queued")
    active_key: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    updated_at: Mapped[float] = mapped_column(Float, default=time.time)
    configuration: Mapped[dict] = mapped_column(JSON)
    reports: Mapped[list] = mapped_column(JSON, default=list)


class SearchJob(Base):
    __tablename__ = "search_jobs"
    __table_args__ = (UniqueConstraint("run_id", "identity", name="uq_run_identity"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(ForeignKey("search_runs.id"), index=True)
    identity: Mapped[str] = mapped_column(String(500))
    company: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(1000))
    url: Mapped[str] = mapped_column(String(4000))
    modality: Mapped[str] = mapped_column(String(20))
    modality_original: Mapped[str] = mapped_column(String(4000))
    location: Mapped[str] = mapped_column(String(4000))
    matches: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
