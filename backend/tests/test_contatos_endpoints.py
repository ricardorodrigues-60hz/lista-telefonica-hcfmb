import pytest
from httpx import AsyncClient
from httpx import ASGITransport
from datetime import datetime, timezone

from app.main import app


from uuid import uuid4


class FakeContato:
    def __init__(self, id=None, nome=None):
        self.id = id or uuid4()
        self.nome = nome
        self.telefone = "(14) 3811-0000"
        self.email = f"{nome.lower().replace(' ', '')}@example.com"
        self.tipo_numero = "institucional"
        self.atualizado_em = datetime.now(timezone.utc)
        self.excluido = False


class FakeRepo:
    def __init__(self, db=None):
        pass

    async def listar_ativos(self):
        return [FakeContato(nome="A"), FakeContato(nome="B")]

    async def salvar_ou_atualizar(self, contato_in, usuario_email):
        return FakeContato(id=contato_in.id, nome=contato_in.nome)

    async def deletar_soft(self, contato_id, usuario_email):
        return True


@pytest.mark.asyncio
async def test_get_contatos(monkeypatch):
    import app.modules.contatos.router as contatos_mod

    monkeypatch.setattr(contatos_mod, "ContatoRepository", lambda db: FakeRepo(db))

    from app.modules.auth.service import get_current_user

    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: type(
        "U", (), {"nome": "Tester", "email": "tester@example.com", "papel": "CONSULTOR"}
    )()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/contatos/")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list) and len(data) == 2


@pytest.mark.asyncio
async def test_consultor_nao_pode_criar_contato(monkeypatch):
    """RBAC: CONSULTOR tem apenas leitura; escrita deve ser bloqueada (403)."""
    import app.modules.contatos.router as contatos_mod

    monkeypatch.setattr(contatos_mod, "ContatoRepository", lambda db: FakeRepo(db))

    from app.modules.auth.service import get_current_user

    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: type(
        "U", (), {"nome": "Tester", "email": "tester@example.com", "papel": "CONSULTOR"}
    )()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            "/api/contatos/criar-editar",
            json={
                "id": str(uuid4()),
                "nome": "Novo Contato",
                "telefone": "(14) 3811-9999",
                "tipo_numero": "publico",
            },
        )

    assert r.status_code == 403


@pytest.mark.asyncio
async def test_gestor_pode_criar_contato(monkeypatch):
    import app.modules.contatos.router as contatos_mod

    monkeypatch.setattr(contatos_mod, "ContatoRepository", lambda db: FakeRepo(db))

    from app.modules.auth.service import get_current_user

    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: type(
        "U", (), {"nome": "Tester", "email": "gestor@example.com", "papel": "GESTOR"}
    )()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            "/api/contatos/criar-editar",
            json={
                "id": str(uuid4()),
                "nome": "Novo Contato",
                "telefone": "(14) 3811-9999",
                "tipo_numero": "publico",
            },
        )

    assert r.status_code == 200


@pytest.mark.asyncio
async def test_listar_contatos_sem_autenticacao_e_negado(monkeypatch):
    """Leitura de contatos agora exige autenticação (ao menos CONSULTOR)."""
    import app.modules.contatos.router as contatos_mod

    monkeypatch.setattr(contatos_mod, "ContatoRepository", lambda db: FakeRepo(db))

    app.dependency_overrides.clear()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/contatos/")

    assert r.status_code == 401
