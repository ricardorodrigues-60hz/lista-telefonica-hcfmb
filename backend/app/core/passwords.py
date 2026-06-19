import asyncio
from typing import Any

"""Async wrappers for blocking password operations.

These helpers run the blocking bcrypt-based functions from `app.core.auth`
in a worker thread via `asyncio.to_thread`, centralizing the pattern and
making call sites simpler and safer.
"""


async def async_get_password_hash(password: str) -> str:
    from app.core.auth import get_password_hash

    return await asyncio.to_thread(get_password_hash, password)


async def async_verify_password(plain_password: str, hashed_password: str) -> bool:
    from app.core.auth import verify_password

    return await asyncio.to_thread(verify_password, plain_password, hashed_password)
