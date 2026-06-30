import pytest
from httpx import AsyncClient
from httpx import ASGITransport

from app.main import app


class DummyUser:
    def __init__(self, usuario_id_externo="gestor-1", papel="GESTOR"):
        self.usuario_id_externo = usuario_id_externo
        self.papel = papel


class FakeRepo:
    def __init__(self):
        self._users = []

    async def listar(self):
        return self._users

    async def buscar_por_id_externo(self, usuario_id_externo: str):
        for u in self._users:
            if u.usuario_id_externo == usuario_id_externo:
                return u
        return None


@pytest.mark.asyncio
async def test_listar_usuarios_as_gestor(monkeypatch):
    fake = FakeRepo()
    fake._users = [
        DummyUser(usuario_id_externo="gestor-1", papel="GESTOR"),
        DummyUser(usuario_id_externo="consultor-2", papel="CONSULTOR")
    ]

    # Override dependencies
    from app.core.auth import get_current_user

    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: DummyUser()

    # Monkeypatch repository used in router
    import app.modules.usuarios.router as usuarios_mod
    monkeypatch.setattr(usuarios_mod, "UsuarioRepository", lambda db: fake)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/usuarios/")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["usuario_id_externo"] == "gestor-1"
    assert data[1]["usuario_id_externo"] == "consultor-2"


@pytest.mark.asyncio
async def test_get_usuario_by_id_externo(monkeypatch):
    fake = FakeRepo()
    user = DummyUser(usuario_id_externo="consultor-2", papel="CONSULTOR")
    fake._users = [user]

    from app.core.auth import get_current_user
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: DummyUser(usuario_id_externo="gestor-1", papel="GESTOR")

    import app.modules.usuarios.router as usuarios_mod
    monkeypatch.setattr(usuarios_mod, "UsuarioRepository", lambda db: fake)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/usuarios/consultor-2")

    assert r.status_code == 200
    data = r.json()
    assert data["usuario_id_externo"] == "consultor-2"
    assert data["papel"] == "CONSULTOR"


@pytest.mark.asyncio
async def test_get_usuario_not_found(monkeypatch):
    fake = FakeRepo()

    from app.core.auth import get_current_user
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: DummyUser()

    import app.modules.usuarios.router as usuarios_mod
    monkeypatch.setattr(usuarios_mod, "UsuarioRepository", lambda db: fake)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/usuarios/non-existent")

    assert r.status_code == 404
