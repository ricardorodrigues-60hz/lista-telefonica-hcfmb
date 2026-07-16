import os
import warnings
import importlib.util
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from typing import AsyncGenerator

from app.core.config import settings

DATABASE_URL = settings.DATABASE_URL

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
