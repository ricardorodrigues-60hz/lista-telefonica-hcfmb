# 📞 Aciono Você — Backend (FastAPI)

API assíncrona (FastAPI + SQLAlchemy 2 async) para a lista telefônica hospitalar, com autenticação JWT, RBAC, soft delete, auditoria e sincronização offline-first. Visão geral do produto: [`../README.md`](../README.md).

## Arquitetura

Organização modular por domínio em `app/modules/<dominio>/`, cada um com `models.py`, `repository.py`, `router.py`, `schemas.py` (e `service.py` quando há regra de negócio não trivial):

| Módulo | Responsabilidade |
|---|---|
| `auth` | login, refresh (rotação), logout, dependências RBAC (`get_current_user`, `require_gestor`, `require_consultor`) |
| `usuarios` | CRUD de usuários (GESTOR) |
| `contatos` | CRUD de contatos + soft delete |
| `sync` | sincronização offline-first (last-write-wins) |
| `auditoria` | `AuditTrail` — registro imutável de escritas |

`app/core/` contém infraestrutura transversal: `config.py` (settings via `.env`), `database.py` (engine/session async), `security.py` (JWT + bcrypt em thread pool), `exceptions.py`, `init_db.py` (seeds), `logging.py`. `app/api.py` agrega os routers dos módulos sob o prefixo `/api`.

## Autenticação e RBAC

- Login por e-mail + senha → access token (JWT curto) + refresh token (persistido como hash, com rotação: cada uso invalida o anterior; reuso de token já rotacionado revoga todas as sessões do usuário).
- `require_gestor` / `require_consultor` são dependências do FastAPI aplicadas por rota; `require_consultor` aceita qualquer papel autenticado.

## Endpoints

| Método | Rota | Papel | Descrição |
|---|---|---|---|
| POST | `/api/auth/login` | — | `{login, senha}` → `{access_token, refresh_token, papel, nome}` |
| POST | `/api/auth/refresh` | — | rotaciona o par de tokens |
| POST | `/api/auth/logout` | — | revoga o refresh token (204) |
| GET | `/api/usuarios/me` | autenticado | dados do usuário atual |
| GET | `/api/usuarios/`, `/{id}` | GESTOR | listar / obter usuário |
| POST/PUT/DELETE | `/api/usuarios/...` | GESTOR | criar / atualizar / soft delete |
| GET | `/api/contatos/` | CONSULTOR+ | lista contatos ativos |
| POST | `/api/contatos/criar-editar` | GESTOR | cria ou edita (payload inclui `id`) |
| POST | `/api/contatos/deletar` | GESTOR | soft delete via `{"id": "<uuid>"}` |
| POST | `/api/sync` | CONSULTOR+ | sync em lote → `{sucesso, contatos_atualizados, error}` |

## Modelos Principais

- **`Usuario`**: `id, nome, email (único), senha_hash, papel (GESTOR/CONSULTOR), excluido`
- **`RefreshToken`**: `id, usuario_id, token_hash, expira_em, revogado`
- **`Contato`**: `id (UUID), nome, telefone, email?, tipo_numero, criado_em, atualizado_em, excluido`
- **`AuditTrail`**: `usuario_nome, acao, tabela, registro_id, detalhes, dados_modificados (JSON), criado_em`

## Instalação e Execução

```bash
python -m venv .venv && .\.venv\Scripts\activate   # source .venv/bin/activate no Linux/macOS
pip install -r requirements.txt

# .env (opcional) — ver variáveis abaixo
alembic upgrade head

RUN_SEEDS=1 uvicorn app.main:app --reload --port 8085
```

Via Docker Compose (a partir da raiz do projeto): `docker compose up -d --build backend`.

### Variáveis de Ambiente

| Variável | Default | Descrição |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///:memory:` | SQLite ou `postgresql+asyncpg://...` |
| `SECRET_KEY` | placeholder | assinatura JWT — trocar em produção |
| `ALGORITHM` | `HS256` | algoritmo JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` / `REFRESH_TOKEN_EXPIRE_DAYS` | `30` / `7` | expiração dos tokens |
| `TOKEN_URL` | `/api/auth/login` | caminho usado pelo Swagger (ajustar se montado como sub-app) |
| `RUN_SEEDS` | `0` | cria tabelas e dados de demonstração no startup |

## Testes

```bash
pytest -v
```

| Arquivo | Cobertura |
|---|---|
| `test_auth_endpoints.py` | login, rotação/reuso de refresh, logout |
| `test_blocking_password_ops.py` | bcrypt fora da thread principal |
| `test_contatos_endpoints.py` | listagem e RBAC de escrita |
| `test_schemas.py` | validação Pydantic |
| `test_sync_endpoints.py` | criação offline, conflito last-write-wins, auth obrigatória |
| `test_usuarios_endpoints.py` | CRUD e RBAC de usuários |

Banco SQLite em memória; CI em `.github/workflows/ci.yml`.

## Troubleshooting

- **`ModuleNotFoundError: No module named 'app'`** — execute os comandos a partir da pasta `backend/` (ou `pytest` na raiz do pacote).
- **CORS no frontend** — `app/main.py` libera `allow_origins=["*"]`; restrinja em produção.
- **401 inesperado** — verifique expiração do access token (`ACCESS_TOKEN_EXPIRE_MINUTES`) e use `/api/auth/refresh`.

## Dependências Principais

`fastapi` · `sqlalchemy[asyncio]` · `aiosqlite` · `pydantic` / `pydantic-settings` · `python-jose` · `bcrypt` · `alembic` · `pytest` / `pytest-asyncio` / `httpx` (testes)
