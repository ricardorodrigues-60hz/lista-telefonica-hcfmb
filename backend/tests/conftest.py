import asyncio
import uuid
from typing import AsyncGenerator

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.main import app
from app.core.config import settings
from app.core.database import Base, get_db

# ---------------------------------------------------------------------
# Engine & Session fixtures (use the same DATABASE_URL from settings)
# ---------------------------------------------------------------------
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)

@pytest.fixture(scope="module")
async def initialize_database() -> None:
    """Create all tables once for the test module."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Drop all tables after the session (optional, fastapi uses in‑memory DB)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

# ---------------------------------------------------------------------
# DB session fixture – provides a fresh AsyncSession per test
# ---------------------------------------------------------------------
@pytest.fixture
async def db_session(initialize_database) -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# ---------------------------------------------------------------------
# Override FastAPI dependencies
# ---------------------------------------------------------------------

@pytest.fixture(autouse=True)
def override_get_db(db_session: AsyncSession):
    """Replace the app's ``get_db`` dependency with the test session.
    This fixture is automatically applied to every test.
    """
    async def _get_db_override() -> AsyncGenerator[AsyncSession, None]:
        yield db_session
    app.dependency_overrides[get_db] = _get_db_override
    yield
    app.dependency_overrides.pop(get_db, None)

# ---------------------------------------------------------------------
# Async client fixture – provides an httpx.AsyncClient bound to the app
# ---------------------------------------------------------------------
@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

# ---------------------------------------------------------------------
# Convenience function to generate a random UUID string
# ---------------------------------------------------------------------
def random_uuid_str() -> str:
    return str(uuid.uuid4())

# ---------------------------------------------------------------------
# Export names for pytest discovery
# ---------------------------------------------------------------------
__all__ = [
    "client",
    "db_session",
    "random_uuid_str",
]
