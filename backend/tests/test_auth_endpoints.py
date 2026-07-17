from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from httpx import ASGITransport

from app.main import app


SENHA_CORRETA = "senha-correta"


class DummyUsuario:
    def __init__(
        self,
        id="user-1",
        email="gestor@hcfmb.unesp.br",
        papel="GESTOR",
        nome="Gestor Teste",
        excluido=False,
    ):
        self.id = id
        self.email = email
        self.papel = papel
        self.nome = nome
        self.senha_hash = "hash-fake"
        self.excluido = excluido


class FakeRefreshRegistro:
    def __init__(self, id, usuario_id, token_hash, expira_em):
        self.id = id
        self.usuario_id = usuario_id
        self.token_hash = token_hash
        self.expira_em = expira_em
        self.revogado = False
        self.substituido_por_id = None


class FakeUsuarioRepo:
    def __init__(self, usuario=None):
        self._usuario = usuario or DummyUsuario()

    async def buscar_por_email(self, email: str):
        return self._usuario if email == self._usuario.email else None

    async def buscar_por_id(self, usuario_id: str):
        return self._usuario if usuario_id == self._usuario.id else None


class FakeRefreshRepo:
    """Réplica em memória do comportamento de RefreshTokenRepository para testes."""

    def __init__(self):
        self._por_hash: dict[str, FakeRefreshRegistro] = {}
        self._contador = 0

    async def criar(self, usuario_id, token_hash, expira_em):
        self._contador += 1
        registro = FakeRefreshRegistro(
            id=f"rt-{self._contador}", usuario_id=usuario_id, token_hash=token_hash, expira_em=expira_em
        )
        self._por_hash[token_hash] = registro
        return registro

    async def buscar_por_hash(self, token_hash):
        return self._por_hash.get(token_hash)

    def esta_valido(self, registro) -> bool:
        if registro.revogado:
            return False
        expira_em = registro.expira_em
        if expira_em.tzinfo is not None:
            expira_em = expira_em.astimezone(timezone.utc).replace(tzinfo=None)
        return expira_em > datetime.now(timezone.utc).replace(tzinfo=None)

    async def revogar_por_token(self, token_hash):
        registro = self._por_hash.get(token_hash)
        if not registro:
            return False
        registro.revogado = True
        return True

    async def revogar_todos_do_usuario(self, usuario_id):
        for registro in self._por_hash.values():
            if registro.usuario_id == usuario_id:
                registro.revogado = True

    async def rotacionar(self, registro_antigo, novo_registro_id):
        registro_antigo.revogado = True
        registro_antigo.substituido_por_id = novo_registro_id


def _sempre_senha_correta(senha_esperada):
    async def _verify(plain_password, hashed_password):
        return plain_password == senha_esperada

    return _verify


def _patch_auth_deps(monkeypatch, usuario=None):
    import app.modules.auth.service as auth_service_mod

    fake_usuarios = FakeUsuarioRepo(usuario)
    fake_refresh = FakeRefreshRepo()

    monkeypatch.setattr(auth_service_mod, "UsuarioRepository", lambda db: fake_usuarios)
    monkeypatch.setattr(auth_service_mod, "RefreshTokenRepository", lambda db: fake_refresh)
    monkeypatch.setattr(auth_service_mod, "async_verify_password", _sempre_senha_correta(SENHA_CORRETA))

    return fake_usuarios, fake_refresh


@pytest.mark.asyncio
async def test_login_sucesso(monkeypatch):
    _patch_auth_deps(monkeypatch)
    app.dependency_overrides.clear()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            "/api/auth/login", json={"login": "gestor@hcfmb.unesp.br", "senha": SENHA_CORRETA}
        )

    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data and "refresh_token" in data
    assert data["papel"] == "GESTOR"
    assert data["nome"] == "Gestor Teste"


@pytest.mark.asyncio
async def test_login_senha_incorreta(monkeypatch):
    _patch_auth_deps(monkeypatch)
    app.dependency_overrides.clear()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            "/api/auth/login", json={"login": "gestor@hcfmb.unesp.br", "senha": "senha-errada"}
        )

    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_usuario_inexistente(monkeypatch):
    _patch_auth_deps(monkeypatch)
    app.dependency_overrides.clear()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            "/api/auth/login", json={"login": "ninguem@hcfmb.unesp.br", "senha": SENHA_CORRETA}
        )

    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_usuario_excluido(monkeypatch):
    usuario = DummyUsuario(excluido=True)
    _patch_auth_deps(monkeypatch, usuario)
    app.dependency_overrides.clear()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            "/api/auth/login", json={"login": usuario.email, "senha": SENHA_CORRETA}
        )

    assert r.status_code == 401


@pytest.mark.asyncio
async def test_refresh_gera_novo_par_e_rotaciona_o_antigo(monkeypatch):
    _patch_auth_deps(monkeypatch)
    app.dependency_overrides.clear()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            "/api/auth/login", json={"login": "gestor@hcfmb.unesp.br", "senha": SENHA_CORRETA}
        )
        assert r.status_code == 200
        refresh_original = r.json()["refresh_token"]

        r2 = await ac.post("/api/auth/refresh", json={"refresh_token": refresh_original})
        assert r2.status_code == 200
        d2 = r2.json()
        assert "access_token" in d2 and "refresh_token" in d2
        assert d2["refresh_token"] != refresh_original

        # Reusar o refresh token já rotacionado deve ser rejeitado (rotação real).
        r3 = await ac.post("/api/auth/refresh", json={"refresh_token": refresh_original})
        assert r3.status_code == 401


@pytest.mark.asyncio
async def test_reuso_de_refresh_token_revoga_todas_as_sessoes(monkeypatch):
    _, fake_refresh = _patch_auth_deps(monkeypatch)
    app.dependency_overrides.clear()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            "/api/auth/login", json={"login": "gestor@hcfmb.unesp.br", "senha": SENHA_CORRETA}
        )
        refresh_original = r.json()["refresh_token"]

        r2 = await ac.post("/api/auth/refresh", json={"refresh_token": refresh_original})
        assert r2.status_code == 200
        refresh_novo = r2.json()["refresh_token"]

        # Reapresentar o token antigo (já rotacionado) deve revogar a sessão nova também.
        r3 = await ac.post("/api/auth/refresh", json={"refresh_token": refresh_original})
        assert r3.status_code == 401

        r4 = await ac.post("/api/auth/refresh", json={"refresh_token": refresh_novo})
        assert r4.status_code == 401


@pytest.mark.asyncio
async def test_logout_revoga_refresh_token(monkeypatch):
    _patch_auth_deps(monkeypatch)
    app.dependency_overrides.clear()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            "/api/auth/login", json={"login": "gestor@hcfmb.unesp.br", "senha": SENHA_CORRETA}
        )
        refresh_token = r.json()["refresh_token"]

        r_logout = await ac.post("/api/auth/logout", json={"refresh_token": refresh_token})
        assert r_logout.status_code == 204

        r_refresh = await ac.post("/api/auth/refresh", json={"refresh_token": refresh_token})
        assert r_refresh.status_code == 401
