import threading

import pytest

from app.core import async_get_password_hash, async_verify_password


@pytest.mark.asyncio
async def test_get_password_hash_runs_in_thread(monkeypatch):
    main_thread = threading.main_thread()

    # Patch sync get_password_hash to assert it runs off the main thread
    def patched_hash(pw: str) -> str:
        assert threading.current_thread() is not main_thread, (
            'get_password_hash ran on main thread'
        )
        return 'hashed'

    import app.core as security_mod

    monkeypatch.setattr(security_mod, 'get_password_hash', patched_hash)

    res = await async_get_password_hash('my-password')
    assert res == 'hashed'


@pytest.mark.asyncio
async def test_verify_password_runs_in_thread(monkeypatch):
    main_thread = threading.main_thread()

    # Patch sync verify_password to assert it runs off the main thread
    def patched_verify(plain: str, hashed: str) -> bool:
        assert threading.current_thread() is not main_thread, (
            'verify_password ran on main thread'
        )
        return True

    import app.core as security_mod

    monkeypatch.setattr(security_mod, 'verify_password', patched_verify)

    res = await async_verify_password('plain', 'hashed')
    assert res is True
