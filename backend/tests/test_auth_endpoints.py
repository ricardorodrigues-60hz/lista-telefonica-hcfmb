import pytest
from httpx import AsyncClient
from httpx import ASGITransport

from app.main import app


class DummyUser:
    def __init__(self, usuario_id_externo="gestor-123", papel="GESTOR"):
        self.usuario_id_externo = usuario_id_externo
        self.papel = papel


class FakeRepo:
    def __init__(self, user=None):
        self._user = user or DummyUser()

    async def buscar_por_id_externo(self, usuario_id_externo: str):
        return self._user


@pytest.mark.asyncio
async def test_login_and_refresh(monkeypatch):
    import app.routers.auth as auth_mod

    monkeypatch.setattr(auth_mod, "UsuarioRepository", lambda db: FakeRepo())

    app.dependency_overrides.clear()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/api/auth/login", json={"usuario_id_externo": "gestor-123"})

        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data and "refresh_token" in data

        # Use refresh token to request a new access token
        refresh = data["refresh_token"]
        r2 = await ac.post("/api/auth/refresh", json={"refresh_token": refresh})
        assert r2.status_code == 200
        d2 = r2.json()
        assert "access_token" in d2 and "refresh_token" in d2
