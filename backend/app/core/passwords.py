import asyncio
from typing import Any
import bcrypt

"""Password utilities.

Provide the blocking bcrypt operations here and async wrappers that
offload them to worker threads. Keeping the blocking functions in this
module avoids circular imports and centralizes password logic.
"""


def get_password_hash(password: str) -> str:
    """Hash a password with bcrypt (blocking)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash (blocking)."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


async def async_get_password_hash(password: str) -> str:
    # Prefer core.auth.get_password_hash if tests or other code monkeypatch it.
    try:
        from app.core.auth import get_password_hash as _core_get
    except Exception:
        _core_get = None

    if _core_get is not None:
        return await asyncio.to_thread(_core_get, password)

    return await asyncio.to_thread(get_password_hash, password)


async def async_verify_password(plain_password: str, hashed_password: str) -> bool:
    # Prefer core.auth.verify_password if available so tests can patch it.
    try:
        from app.core.auth import verify_password as _core_verify
    except Exception:
        _core_verify = None

    if _core_verify is not None:
        return await asyncio.to_thread(_core_verify, plain_password, hashed_password)

    return await asyncio.to_thread(verify_password, plain_password, hashed_password)
