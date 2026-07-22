from datetime import datetime, timezone
from http import HTTPStatus

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.modules.auth import get_current_user


class DummyUsuario:
    def __init__(
        self,
        id='gestor-1',
        email='gestor@hcfmb.unesp.br',
        papel='GESTOR',
        nome='Gestor',
        excluido=False,
    ):
        self.id = id
        self.email = email
        self.papel = papel
        self.nome = nome
        self.excluido = excluido
        self.criado_em = datetime.now(timezone.utc)
        self.atualizado_em = datetime.now(timezone.utc)


class FakeUsuarioRepo:
    def __init__(self):
        self._usuarios: list[DummyUsuario] = []

    async def listar_ativos(self):
        return [u for u in self._usuarios if not u.excluido]

    async def buscar_por_id(self, usuario_id: str):
        for u in self._usuarios:
            if u.id == usuario_id:
                return u
        return None

    async def buscar_por_email(self, email: str):
        for u in self._usuarios:
            if u.email == email:
                return u
        return None

    async def criar(self, *, nome, email, senha, papel, autor):
        novo = DummyUsuario(
            id=f'user-{len(self._usuarios) + 1}',
            email=email,
            papel=papel,
            nome=nome,
        )
        self._usuarios.append(novo)
        return novo

    async def atualizar(
        self, usuario, *, autor, nome=None, papel=None, senha=None
    ):
        if nome is not None:
            usuario.nome = nome
        if papel is not None:
            usuario.papel = papel
        return usuario

    async def deletar_soft(self, usuario, *, autor):
        usuario.excluido = True


def _override_usuario_atual(monkeypatch, fake_repo, usuario_atual):
    import app.modules.usuarios as usuarios_mod

    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: usuario_atual
    monkeypatch.setattr(
        usuarios_mod, 'UsuarioRepository', lambda db: fake_repo
    )


@pytest.mark.asyncio
async def test_listar_usuarios_como_gestor(monkeypatch):
    fake = FakeUsuarioRepo()
    fake._usuarios = [
        DummyUsuario(
            id='gestor-1', email='gestor@hcfmb.unesp.br', papel='GESTOR'
        ),
        DummyUsuario(
            id='consultor-2',
            email='consultor@hcfmb.unesp.br',
            papel='CONSULTOR',
        ),
    ]
    _override_usuario_atual(monkeypatch, fake, DummyUsuario())

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url='http://test'
    ) as ac:
        r = await ac.get('/api/usuarios/')

    assert r.status_code == HTTPStatus.OK
    data = r.json()
    assert len(data) == 2
    assert data[0]['email'] == 'gestor@hcfmb.unesp.br'


@pytest.mark.asyncio
async def test_listar_usuarios_negado_para_consultor(monkeypatch):
    fake = FakeUsuarioRepo()
    consultor = DummyUsuario(
        id='consultor-2', email='consultor@hcfmb.unesp.br', papel='CONSULTOR'
    )
    _override_usuario_atual(monkeypatch, fake, consultor)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url='http://test'
    ) as ac:
        r = await ac.get('/api/usuarios/')

    assert r.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
async def test_obter_usuario_por_id(monkeypatch):
    fake = FakeUsuarioRepo()
    fake._usuarios = [
        DummyUsuario(
            id='consultor-2',
            email='consultor@hcfmb.unesp.br',
            papel='CONSULTOR',
        )
    ]
    _override_usuario_atual(monkeypatch, fake, DummyUsuario())

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url='http://test'
    ) as ac:
        r = await ac.get('/api/usuarios/consultor-2')

    assert r.status_code == HTTPStatus.OK
    data = r.json()
    assert data['email'] == 'consultor@hcfmb.unesp.br'
    assert data['papel'] == 'CONSULTOR'


@pytest.mark.asyncio
async def test_obter_usuario_nao_encontrado(monkeypatch):
    fake = FakeUsuarioRepo()
    _override_usuario_atual(monkeypatch, fake, DummyUsuario())

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url='http://test'
    ) as ac:
        r = await ac.get('/api/usuarios/nao-existe')

    assert r.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_criar_usuario_como_gestor(monkeypatch):
    fake = FakeUsuarioRepo()
    _override_usuario_atual(monkeypatch, fake, DummyUsuario())

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url='http://test'
    ) as ac:
        r = await ac.post(
            '/api/usuarios/',
            json={
                'nome': 'Novo Consultor',
                'email': 'novo@hcfmb.unesp.br',
                'senha': 'senha123',
                'papel': 'CONSULTOR',
            },
        )

    assert r.status_code == HTTPStatus.CREATED
    data = r.json()
    assert data['email'] == 'novo@hcfmb.unesp.br'
    assert data['papel'] == 'CONSULTOR'


@pytest.mark.asyncio
async def test_criar_usuario_email_duplicado(monkeypatch):
    fake = FakeUsuarioRepo()
    fake._usuarios = [DummyUsuario(email='duplicado@hcfmb.unesp.br')]
    _override_usuario_atual(monkeypatch, fake, DummyUsuario())

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url='http://test'
    ) as ac:
        r = await ac.post(
            '/api/usuarios/',
            json={
                'nome': 'Outro',
                'email': 'duplicado@hcfmb.unesp.br',
                'senha': 'senha123',
                'papel': 'CONSULTOR',
            },
        )

    assert r.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.asyncio
async def test_excluir_usuario_nao_pode_ser_o_proprio(monkeypatch):
    fake = FakeUsuarioRepo()
    gestor = DummyUsuario(id='gestor-1')
    fake._usuarios = [gestor]
    _override_usuario_atual(monkeypatch, fake, gestor)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url='http://test'
    ) as ac:
        r = await ac.delete('/api/usuarios/gestor-1')

    assert r.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.asyncio
async def test_excluir_usuario_com_sucesso(monkeypatch):
    fake = FakeUsuarioRepo()
    gestor = DummyUsuario(id='gestor-1')
    outro = DummyUsuario(
        id='consultor-2', email='consultor@hcfmb.unesp.br', papel='CONSULTOR'
    )
    fake._usuarios = [gestor, outro]
    _override_usuario_atual(monkeypatch, fake, gestor)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url='http://test'
    ) as ac:
        r = await ac.delete('/api/usuarios/consultor-2')

    assert r.status_code == HTTPStatus.NO_CONTENT
    assert outro.excluido is True
