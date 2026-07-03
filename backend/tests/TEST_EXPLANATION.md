# TEST_EXPLANATION.md

## Como executar os testes
```bash
# Instale as dependências de desenvolvimento (pytest, pytest‑asyncio, httpx)
pip install -r requirements.txt
# Rode a bateria de testes
pytest -v
```

O comando acima executa todos os arquivos dentro da pasta `tests/`. O `-v` (verbose) mostra detalhes de cada teste.

## Fixtures e mocks criados em `tests/conftest.py`
| Fixture | O que faz | Como é usado |
|---------|-----------|--------------|
| `engine` / `AsyncSessionLocal` | Cria um engine SQLAlchemy assíncrono usando a mesma `DATABASE_URL` definidia em `app.core.config.Settings`. | Compartilhado por todas as fixtures. |
| `initialize_database` (session) | Cria todas as tabelas antes da primeira execução de teste e as remove ao final da sessão. | É dependência de `db_session`. |
| `db_session` | Fornece um `AsyncSession` limpo para **cada** teste. | Injetado nos testes via parâmetro. |
| `override_get_db` (autouse) | Substitui a dependência `app.core.database.get_db` da aplicação pela sessão de teste. | Aplicado automaticamente a todos os testes. |
| `client` | Instância de `httpx.AsyncClient` já configurada com a aplicação FastAPI. | Usada para fazer chamadas HTTP assíncronas aos endpoints. |
| `create_user_permission` | Função helper que insere (ou atualiza) um registro de permissão (`GESTOR` ou `CONSULTOR`) na tabela `usuarios`. | Chamado nos testes para preparar o papel do usuário. |
| `random_uuid_str` | Gera um UUID aleatório em string – útil para criar IDs únicos nos payloads. | Utilizado nos testes quando necessário. |

### Mock de autenticação baseada em token (header `x-user-id`)
O backend espera o cabeçalho HTTP `x-user-id` contendo o **ID externo** do usuário. A dependência `get_current_user` (arquivo `app/core/auth/service.py`) lê esse cabeçalho, consulta a tabela `usuarios` e devolve um objeto `UsuarioAutenticado` com os atributos `usuario_id_externo` e `papel`.

Nos testes simulamos isso enviando o cabeçalho nas requisições:
```python
headers = {"x-user-id": "gestor-1"}
response = await client.post("/contatos/criar-editar", json=payload, headers=headers)
```
Se o papel for **GESTOR**, a dependência `require_gestor` permite a operação; se for **CONSULTOR**, a rota levanta `HTTPException(403)`.

## Explicação linha‑a‑linha dos testes (`tests/test_contatos.py`)
```python
# Importa utilitários padrão e os schemas Pydantic usados pelos endpoints
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.contatos.schemas import ContatoCreate, ContatoSync, SyncPayload
```

### `contato_create_payload`
Função helper que cria um dicionário JSON válido a partir do modelo `ContatoCreate`. O UUID é gerado dinamicamente para garantir unicidade.
```python
def contato_create_payload(user_id: str) -> dict:
    return ContatoCreate(
        id=uuid.uuid4(),
        nome="Teste Usuário",
        telefone="+55 (11) 91234-5678",
        email="teste@example.com",
        tipo_numero="PUBLICO",
    ).dict()
```

### `test_get_contatos_empty`
1. Faz **GET** `/contatos` sem nenhum registro no banco.
2. Verifica **200 OK**.
3. Confirma que a lista retornada está vazia.
```python
response = await client.get("/contatos")
assert response.status_code == 200
assert response.json() == []
```

### `test_create_contato_success`
1. Cria permissão **GESTOR** para o ID `gestor-1`.
2. Envia payload de criação usando o cabeçalho `x-user-id`.
3. Assegura **200 OK** e verifica se os campos retornados correspondem ao que foi enviado.
```python
await create_user_permission(db_session, gestor_id, role="GESTOR")
payload = contato_create_payload(gestor_id)
response = await client.post("/contatos/criar-editar", json=payload, headers={"x-user-id": gestor_id})
```

### `test_create_contato_forbidden`
Similar ao anterior, porém a permissão é **CONSULTOR**. O endpoint deve responder **403** com a mensagem de erro esperada.
```python
await create_user_permission(db_session, consultor_id, role="CONSULTOR")
response = await client.post(...)
assert response.status_code == 403
assert response.json()["detail"] == "Operação permitida apenas para Gestores."
```

### `test_delete_contato_success`
1. Cria um contato como gestor.
2. Executa **POST** `/contatos/deletar` com o ID do contato.
3. Verifica a mensagem de sucesso.
4. Usa o repositório para confirmar que o campo `excluido` ficou `True`.
```python
repo = ContatoRepository(db_session)
contato = await repo.buscar_por_id(contato_id)
assert contato.excluido is True
```

### `test_sync_contatos`
1. Cria um contato inicial.
2. Monta um payload `SyncPayload` contendo:
   - Uma atualização do contato já existente (alterando nome, telefone, etc.).
   - Um novo contato totalmente novo.
3. Envia **POST** `/contatos/sync`.
4. Assegura que a resposta indica sucesso e que **ambos os IDs** (o antigo e o novo) são retornados em `contatos_atualizados`.
```python
sync_payload = SyncPayload(contatos=sync_contacts)
resp = await client.post("/contatos/sync", json=sync_payload.dict(), headers={"x-user-id": gestor_id})
assert resp.status_code == 200
assert set(resp.json()["contatos_atualizados"]) == {str(existing_id), str(new_id)}
```

## Extensões futuras
- **Cobertura de auditoria**: pode‑se adicionar um fixture que verifica a tabela `audit_trail` após cada operação.
- **CI/CD**: integrar `pytest --cov` em pipelines GitHub Actions para garantir que a cobertura não caia abaixo de 90 %.
- **Testes de erro de validação**: testar telefones inválidos, campos ausentes, etc.


