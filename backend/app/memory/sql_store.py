"""Database-backed agent state and session memory store with in-memory fallback."""

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.core.config import get_settings
from app.db.models import ThreadCheckpoint
from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


class SQLStateStore:
    """Persists LangGraph thread checkpoints and agent memory in PostgreSQL (Neon) or SQLite.

    Provides high availability across serverless container restarts and scales to zero
    without ongoing idle costs. Automatically falls back to local in-memory storage
    if the database is temporarily unreachable.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self._local_cache: dict[str, dict[str, Any]] = {}

    @property
    def backend_mode(self) -> str:
        """Return active state backend mode ('postgres' or 'sqlite')."""
        return "postgres" if self.settings.is_postgres else "sqlite"

    async def save_checkpoint(self, thread_id: str, state_payload: dict[str, Any]) -> None:
        """Persist thread state snapshot to database or in-memory fallback."""
        record = {
            "thread_id": thread_id,
            "state": state_payload,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        try:
            async with AsyncSessionLocal() as session:
                existing = await session.get(ThreadCheckpoint, thread_id)
                if existing:
                    existing.state = state_payload
                    existing.updated_at = datetime.now(UTC)
                else:
                    checkpoint = ThreadCheckpoint(
                        thread_id=thread_id,
                        state=state_payload,
                        updated_at=datetime.now(UTC),
                    )
                    session.add(checkpoint)
                await session.commit()
                return
        except Exception as exc:
            logger.warning("Database checkpoint save failed (%s); caching in memory.", exc)

        self._local_cache[thread_id] = record

    async def load_checkpoint(self, thread_id: str) -> dict[str, Any] | None:
        """Load the latest thread state snapshot from database or in-memory fallback."""
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(ThreadCheckpoint).where(ThreadCheckpoint.thread_id == thread_id)
                result = await session.execute(stmt)
                checkpoint = result.scalar_one_or_none()
                if checkpoint is not None:
                    return {
                        "thread_id": checkpoint.thread_id,
                        "state": checkpoint.state,
                        "updated_at": (
                            checkpoint.updated_at.isoformat()
                            if checkpoint.updated_at
                            else datetime.now(UTC).isoformat()
                        ),
                    }
        except Exception as exc:
            logger.warning("Database checkpoint read failed (%s); reading from memory.", exc)

        return self._local_cache.get(thread_id)


state_store = SQLStateStore()
