from uuid import uuid4
from pydantic import ValidationError

from app.modules.contatos.schemas import ContatoCreate
from app.modules.auth.schemas import LoginRequest
from app.modules.usuarios.schemas import UsuarioCreate


def test_contato_create_valid():
    c = ContatoCreate(id=uuid4(), nome="Fulano", telefone="+5511999999999", tipo_numero="institucional")
    assert c.nome == "Fulano"


def test_contato_invalid_phone():
    try:
        ContatoCreate(id=uuid4(), nome="Ciclano", telefone="bad-phone", tipo_numero="publico")
        assert False, "Telefone inválido deveria gerar ValidationError"
    except ValidationError:
        assert True


def test_login_request_valid():
    lr = LoginRequest(login="gestor@hcfmb.unesp.br", senha="gestor123")
    assert lr.login == "gestor@hcfmb.unesp.br"
    assert lr.senha == "gestor123"


def test_login_request_email_invalido():
    try:
        LoginRequest(login="nao-e-um-email", senha="gestor123")
        assert False, "E-mail inválido deveria gerar ValidationError"
    except ValidationError:
        assert True


def test_usuario_create_valid():
    u = UsuarioCreate(nome="Novo Usuário", email="novo@hcfmb.unesp.br", senha="senha123", papel="CONSULTOR")
    assert u.papel == "CONSULTOR"


def test_usuario_create_papel_validation():
    try:
        UsuarioCreate(nome="Alguém", email="alguem@hcfmb.unesp.br", senha="senha123", papel="ADMIN")
        assert False, "Papel inválido deveria causar ValidationError"
    except ValidationError:
        assert True
