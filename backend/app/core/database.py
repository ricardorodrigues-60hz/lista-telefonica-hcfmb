import os
import warnings
import importlib.util
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from typing import AsyncGenerator

# Default DATABASE_URL behavior:
# - If the environment variable DATABASE_URL is set, use it (allows PostgreSQL in prod/CI).
# - If not set, default to an in-memory SQLite (aiosqlite) to make local testing easy.
# - If a postgresql+asyncpg URL is provided but asyncpg is missing, fall back to sqlite.
_env_db = os.getenv("DATABASE_URL")

def _choose_database_url(url: str | None) -> str:
    if not url:
        return "sqlite+aiosqlite:///:memory:"
    # If user provided a postgres+asyncpg URL but asyncpg isn't installed, warn and fall back
    if url.startswith("postgresql+asyncpg") and importlib.util.find_spec("asyncpg") is None:
        warnings.warn(
            "asyncpg not installed; falling back to in-memory sqlite+aiosqlite for tests",
            RuntimeWarning,
        )
        return "sqlite+aiosqlite:///:memory:"
    return url


DATABASE_URL = _choose_database_url(_env_db)

# Create async engine and session maker
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
)

async_session_maker = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
