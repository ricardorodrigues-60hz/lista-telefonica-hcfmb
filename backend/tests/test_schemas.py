# from uuid import uuid4
# from pydantic import ValidationError

# from app.modules.contatos.schemas import ContatoCreate


# def test_contato_create_valid():
#     c = ContatoCreate(id=uuid4(), nome="Fulano", telefone="+5511999999999", tipo_numero="institucional")
#     assert c.nome == "Fulano"


# def test_contato_invalid_phone():
#     try:
#         ContatoCreate(id=uuid4(), nome="Ciclano", telefone="bad-phone", tipo_numero="publico")
#         assert False, "Telefone inválido deveria gerar ValidationError"
#     except ValidationError:
#         assert True
