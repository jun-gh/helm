"""Relational models for agent orchestration telemetry and audit logs."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarative class for SQLAlchemy ORM models."""


class OrchestrationRunLog(Base):
    """Stores high-level execution history of Helm multi-agent runs."""

    __tablename__ = "orchestration_run_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    thread_id: Mapped[str] = mapped_column(String(64), index=True)
    objective: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="completed")
    final_output: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class ThreadCheckpoint(Base):
    """Stores LangGraph thread state checkpoints in PostgreSQL / SQLite."""

    __tablename__ = "thread_checkpoints"

    thread_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    state: Mapped[dict[str, Any]] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
