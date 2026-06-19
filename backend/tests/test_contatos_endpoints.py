import pytest
from httpx import AsyncClient
from datetime import datetime, timezone

from app.main import app


class FakeContato:
    def __init__(self, id, nome):
        self.id = id
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
        return [FakeContato("id1", "A"), FakeContato("id2", "B")]

    async def sincronizar_lote_offline(self, contatos, usuario_nome):
        # pretend we updated the first contact
        return [c.get("id") for c in contatos if c.get("id")]


@pytest.mark.asyncio
async def test_get_contatos_and_sync(monkeypatch):
    import app.routers.contatos as contatos_mod

    monkeypatch.setattr(contatos_mod, "ContatoRepository", lambda db: FakeRepo(db))

    # override auth dependency for sync endpoint
    app.dependency_overrides.clear()
    app.dependency_overrides["get_current_user"] = lambda: type("U", (), {"nome": "Tester"})()

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/api/contatos/")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list) and len(data) == 2

        payload = {"contatos": [{"id": "id1", "nome": "A"}]}
        r2 = await ac.post("/api/contatos/sync", json=payload)
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2.get("sucesso") is True
