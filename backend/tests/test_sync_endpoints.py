from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.modules.auth import get_current_user


class FakeContato:
    def __init__(
        self,
        id,
        nome,
        telefone,
        email,
        tipo_numero,
        atualizado_em,
        excluido=False,
    ):
        self.id = str(id)
        self.nome = nome
        self.telefone = telefone
        self.email = email
        self.tipo_numero = tipo_numero
        self.atualizado_em = atualizado_em
        self.excluido = excluido


class FakeContatoRepository:
    """Substitui o ContatoRepository real para isolar o SyncService nos testes."""

    def __init__(self, db=None):
        self._por_id: dict[str, FakeContato] = {}

    async def buscar_por_id(self, contato_id: str):
        return self._por_id.get(contato_id)

    def criar_do_offline(
        self,
        *,
        id,
        nome,
        telefone,
        email,
        tipo_numero,
        excluido,
        timestamp,
        usuario_nome,
    ):
        contato = FakeContato(
            id, nome, telefone, email, tipo_numero, timestamp, excluido
        )
        self._por_id[str(id)] = contato
        return contato

    def atualizar_do_offline(
        self,
        contato,
        *,
        nome,
        telefone,
        email,
        tipo_numero,
        excluido,
        timestamp,
        usuario_nome,
    ):
        contato.nome = nome
        contato.telefone = telefone
        contato.email = email
        contato.tipo_numero = tipo_numero
        contato.excluido = excluido
        contato.atualizado_em = timestamp
        return contato


def _override_usuario_atual(papel='CONSULTOR'):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = type(
        'U',
        (),
        {'nome': 'Tester', 'email': 'tester@example.com', 'papel': papel},
    )


@pytest.mark.asyncio
async def test_sync_cria_contato_novo(monkeypatch):
    import app.modules.sync as sync_service_mod

    fake_repo = FakeContatoRepository()
    monkeypatch.setattr(
        sync_service_mod, 'ContatoRepository', lambda db: fake_repo
    )

    _override_usuario_atual()

    novo_id = str(uuid4())
    payload = {
        'contatos': [
            {
                'id': novo_id,
                'nome': 'Criado Offline',
                'telefone': '(14) 3811-2222',
                'email': 'offline@example.com',
                'tipo_numero': 'publico',
                'atualizado_em': datetime.now(timezone.utc).isoformat(),
                'excluido': False,
            }
        ]
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url='http://test'
    ) as ac:
        r = await ac.post('/api/sync', json=payload)

    assert r.status_code == HTTPStatus.OK
    data = r.json()
    assert data['sucesso'] is True
    assert novo_id in data['contatos_atualizados']
    assert fake_repo._por_id[novo_id].nome == 'Criado Offline'


@pytest.mark.asyncio
async def test_sync_conflito_aplica_last_write_wins(monkeypatch):
    """Alteração offline mais recente que o servidor deve prevalecer."""
    import app.modules.sync as sync_service_mod

    fake_repo = FakeContatoRepository()
    contato_id = str(uuid4())
    timestamp_servidor = datetime.now(timezone.utc).replace(
        tzinfo=None
    ) - timedelta(hours=1)
    fake_repo._por_id[contato_id] = FakeContato(
        contato_id,
        'Nome Antigo',
        '(14) 0000-0000',
        'antigo@example.com',
        'publico',
        timestamp_servidor,
    )

    monkeypatch.setattr(
        sync_service_mod, 'ContatoRepository', lambda db: fake_repo
    )
    _override_usuario_atual()

    payload = {
        'contatos': [
            {
                'id': contato_id,
                'nome': 'Nome Atualizado Offline',
                'telefone': '(14) 9999-9999',
                'email': 'novo@example.com',
                'tipo_numero': 'publico',
                'atualizado_em': datetime.now(timezone.utc).isoformat(),
                'excluido': False,
            }
        ]
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url='http://test'
    ) as ac:
        r = await ac.post('/api/sync', json=payload)

    assert r.status_code == HTTPStatus.OK
    assert fake_repo._por_id[contato_id].nome == 'Nome Atualizado Offline'


@pytest.mark.asyncio
async def test_sync_conflito_ignora_alteracao_desatualizada(monkeypatch):
    """Alteração offline mais antiga que o servidor deve ser descartada."""
    import app.modules.sync as sync_service_mod

    fake_repo = FakeContatoRepository()
    contato_id = str(uuid4())
    timestamp_servidor = datetime.now(timezone.utc).replace(tzinfo=None)
    fake_repo._por_id[contato_id] = FakeContato(
        contato_id,
        'Nome do Servidor',
        '(14) 1111-1111',
        'servidor@example.com',
        'publico',
        timestamp_servidor,
    )

    monkeypatch.setattr(
        sync_service_mod, 'ContatoRepository', lambda db: fake_repo
    )
    _override_usuario_atual()

    payload = {
        'contatos': [
            {
                'id': contato_id,
                'nome': 'Nome Offline Desatualizado',
                'telefone': '(14) 9999-9999',
                'email': 'offline@example.com',
                'tipo_numero': 'publico',
                'atualizado_em': (
                    datetime.now(timezone.utc) - timedelta(hours=2)
                ).isoformat(),
                'excluido': False,
            }
        ]
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url='http://test'
    ) as ac:
        r = await ac.post('/api/sync', json=payload)

    assert r.status_code == HTTPStatus.OK
    # Servidor mantém o nome original: alteração offline mais antiga foi descartada.
    assert fake_repo._por_id[contato_id].nome == 'Nome do Servidor'


@pytest.mark.asyncio
async def test_sync_requer_autenticacao(monkeypatch):
    import app.modules.sync as sync_service_mod

    monkeypatch.setattr(
        sync_service_mod,
        'ContatoRepository',
        lambda db: FakeContatoRepository(),
    )
    app.dependency_overrides.clear()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url='http://test'
    ) as ac:
        r = await ac.post('/api/sync', json={'contatos': []})

    assert r.status_code == HTTPStatus.UNAUTHORIZED
