from uuid import uuid4
from pydantic import ValidationError

from app.schemas.contatos import ContatoCreate
from app.schemas.auth import LoginRequest
from app.schemas.usuarios import UsuarioCreate


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
    lr = LoginRequest(usuario_id_externo="gestor-123")
    assert lr.usuario_id_externo == "gestor-123"


def test_usuario_create_papel_validation():
    try:
        UsuarioCreate(usuario_id_externo="some-id", papel="ADMIN")
        assert False, "Papel inválido deveria causar ValidationError"
    except ValidationError:
        assert True
