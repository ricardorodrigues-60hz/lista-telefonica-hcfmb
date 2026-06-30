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

    async def sincronizar_lote_offline(self, contatos, usuario_nome):
        # pretend we updated the first contact
        ids = []
        for c in contatos:
            try:
                # pydantic model: has attribute `id`
                ids.append(str(c.id))
            except Exception:
                # dict-like
                if isinstance(c, dict) and c.get("id"):
                    ids.append(str(c.get("id")))
        return ids


@pytest.mark.asyncio
async def test_get_contatos_and_sync(monkeypatch):
    import app.modules.contatos.router as contatos_mod

    monkeypatch.setattr(contatos_mod, "ContatoRepository", lambda db: FakeRepo(db))

    # override auth dependency for sync endpoint
    from app.core.auth import get_current_user

    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: type("U", (), {"nome": "Tester"})()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/contatos/")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list) and len(data) == 2

        payload = {"contatos": [data[0]]}
        r2 = await ac.post("/api/contatos/sync", json=payload)
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2.get("sucesso") is True
