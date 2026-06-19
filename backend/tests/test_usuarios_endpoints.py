import pytest
from httpx import AsyncClient
from httpx import ASGITransport

from app.main import app


class DummyUser:
    def __init__(self, id=1, email="admin@example.com", nome="Admin", papel="GESTOR"):
        self.id = id
        self.email = email
        self.nome = nome
        self.papel = papel


class FakeRepo:
    def __init__(self):
        self._users = []

    async def listar(self):
        return self._users

    async def buscar_por_id(self, user_id: int):
        for u in self._users:
            if u.id == user_id:
                return u
        return None

    async def criar(self, email: str, nome: str, senha_hash: str, papel: str):
        new = DummyUser(id=(len(self._users) + 1), email=email, nome=nome, papel=papel)
        self._users.append(new)
        return new


@pytest.mark.asyncio
async def test_listar_usuarios_as_gestor(monkeypatch):
    fake = FakeRepo()
    fake._users = [DummyUser(id=1, email="a@example.com", nome="A", papel="GESTOR"), DummyUser(id=2, email="b@example.com", nome="B", papel="CONSULTOR")]

    # Override dependencies
    from app.core.auth import get_current_user, require_gestor

    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: DummyUser()
    app.dependency_overrides[require_gestor] = lambda: DummyUser()
    app.dependency_overrides["require_gestor"] = lambda: DummyUser()

    # Monkeypatch repository used in router
    import app.routers.usuarios as usuarios_mod

    monkeypatch.setattr(usuarios_mod, "UsuarioRepository", lambda db: fake)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/usuarios/")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 2


@pytest.mark.asyncio
async def test_criar_usuario(monkeypatch):
    fake = FakeRepo()

    from app.core.auth import require_gestor

    app.dependency_overrides.clear()
    app.dependency_overrides[require_gestor] = lambda: DummyUser()

    import app.routers.usuarios as usuarios_mod
    monkeypatch.setattr(usuarios_mod, "UsuarioRepository", lambda db: fake)

    payload = {"email": "new@example.com", "nome": "New", "papel": "CONSULTOR", "senha": "pass123"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/api/usuarios/", json=payload)

    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "new@example.com"
    assert body["nome"] == "New"


@pytest.mark.asyncio
async def test_get_usuario_not_found(monkeypatch):
    fake = FakeRepo()

    from app.core.auth import get_current_user

    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: DummyUser()

    import app.routers.usuarios as usuarios_mod
    monkeypatch.setattr(usuarios_mod, "UsuarioRepository", lambda db: fake)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/usuarios/999")

    assert r.status_code == 404
