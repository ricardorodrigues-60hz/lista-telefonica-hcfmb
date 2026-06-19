import os
import warnings
import importlib.util
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# Default DATABASE_URL (can be overridden by environment)
_default_db = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://usuario:senha@localhost:5432/nome_do_banco",
)

# If the configured URL requires asyncpg but it's not installed (common in test envs),
# fall back to an in-memory sqlite+aiosqlite database so tests can import modules
# without raising ModuleNotFoundError for asyncpg.
def _choose_database_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg"):
        if importlib.util.find_spec("asyncpg") is None:
            warnings.warn(
                "asyncpg not installed; falling back to in-memory sqlite+aiosqlite for tests",
                RuntimeWarning,
            )
            return "sqlite+aiosqlite:///:memory:"
    return url

DATABASE_URL = _choose_database_url(_default_db)

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


async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
