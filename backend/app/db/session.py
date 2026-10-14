"""Async SQLAlchemy engine configured for local SQLite and Neon Serverless Postgres."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


def build_engine() -> AsyncEngine:
    """Build AsyncEngine tailored to SQLite (local) or Neon Serverless Postgres (prod).

    Uses NullPool on Postgres so serverless compute on Render and Neon can
    cleanly scale to zero without holding idle connections open.
    """
    settings = get_settings()
    if settings.is_postgres:
        return create_async_engine(
            settings.database_url,
            poolclass=NullPool,
            echo=False,
        )
    return create_async_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        echo=False,
    )


engine: AsyncEngine = build_engine()
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency providing a scoped AsyncSession."""
    async with AsyncSessionLocal() as session:
        yield session
