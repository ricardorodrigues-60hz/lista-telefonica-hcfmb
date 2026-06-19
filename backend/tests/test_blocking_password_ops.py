import threading
import pytest
from httpx import AsyncClient

from app.main import app


class DummyUserObj:
    def __init__(self, login="user@example.com", nome="User", papel="GESTOR", senha_hash="hash"):
        self.login = login
        self.nome = nome
        self.papel = papel
        self.senha_hash = senha_hash


class FakeRepo:
    def __init__(self, user=None):
        self._user = user or DummyUserObj()

    async def buscar_por_login(self, login: str):
        return self._user


@pytest.mark.asyncio
async def test_verify_password_runs_in_thread(monkeypatch):
    main_thread = threading.main_thread()

    # Replace UsuarioRepository used by the auth router with a fake that returns a user
    import app.routers.auth as auth_mod

    monkeypatch.setattr(auth_mod, "UsuarioRepository", lambda db: FakeRepo())

    # Patch verify_password to assert it's running off the main thread
    def patched_verify(plain, hashed):
        assert threading.current_thread() is not main_thread, "verify_password ran on main thread"
        return True

    import app.core.auth as core_auth
    monkeypatch.setattr(core_auth, "verify_password", patched_verify)

    app.dependency_overrides.clear()

    async with AsyncClient(app=app, base_url="http://test") as ac:
        payload = {"login": "user@example.com", "senha": "passw"}
        r = await ac.post("/api/auth/login", json=payload)

    assert r.status_code == 200


@pytest.mark.asyncio
async def test_get_password_hash_runs_in_thread(monkeypatch):
    main_thread = threading.main_thread()

    # Patch get_password_hash to assert it's running off the main thread
    def patched_hash(pw: str) -> str:
        assert threading.current_thread() is not main_thread, "get_password_hash ran on main thread"
        return "hashed"

    import app.core.auth as core_auth
    monkeypatch.setattr(core_auth, "get_password_hash", patched_hash)

    # Patch UsuarioRepository in usuarios router to capture criar call
    import app.routers.usuarios as usuarios_mod

    class FakeUserRepo2:
        def __init__(self, db):
            pass

        async def criar(self, email, nome, senha_hash, papel):
            # return an object compatible with UsuarioResponse.from_orm
            class U:
                def __init__(self, email, nome, papel):
                    self.id = 1
                    self.email = email
                    self.nome = nome
                    self.papel = papel

            return U(email, nome, papel)

    monkeypatch.setattr(usuarios_mod, "UsuarioRepository", lambda db: FakeUserRepo2(db))

    # Override auth dependency to allow creation
    app.dependency_overrides.clear()
    app.dependency_overrides["require_gestor"] = lambda: DummyUserObj()

    async with AsyncClient(app=app, base_url="http://test") as ac:
        payload = {"email": "n@example.com", "nome": "N", "papel": "CONSULTOR", "senha": "pw"}
        r = await ac.post("/api/usuarios/", json=payload)

    assert r.status_code == 201
