import pytest
from httpx import AsyncClient
from httpx import ASGITransport

from app.main import app


class DummyUser:
    def __init__(self, login="user@example.com", nome="User", papel="GESTOR", senha_hash="hash"):
        self.login = login
        self.nome = nome
        self.papel = papel
        self.senha_hash = senha_hash


class FakeRepo:
    def __init__(self, user=None):
        self._user = user or DummyUser()

    async def buscar_por_login(self, login: str):
        return self._user


@pytest.mark.asyncio
async def test_login_and_refresh(monkeypatch):
    # Replace repository and password verification to isolate endpoint logic
    import app.routers.auth as auth_mod

    monkeypatch.setattr(auth_mod, "UsuarioRepository", lambda db: FakeRepo())

    async def fake_verify(plain, hashed):
        return True

    # auth router imported the helper directly; patch the router reference
    import app.routers.auth as auth_mod2
    monkeypatch.setattr(auth_mod2, "async_verify_password", fake_verify)

    app.dependency_overrides.clear()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/api/auth/login", json={"login": "user@example.com", "senha": "pw"})

        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data and "refresh_token" in data

        # Use refresh token to request a new access token
        refresh = data["refresh_token"]
        r2 = await ac.post("/api/auth/refresh", json={"refresh_token": refresh})
        assert r2.status_code == 200
        d2 = r2.json()
        assert "access_token" in d2 and "refresh_token" in d2
