# 📞 Aciono Você — Lista Telefônica Hospitalar (PWA Offline-First)
### HCFMB · UNESP

Sistema de contatos/ramais institucionais com sincronização offline-first: os dados vivem no IndexedDB do navegador (Dexie.js) e são sincronizados com o backend (FastAPI + SQLAlchemy async) via last-write-wins baseado em timestamp UTC.

Docs específicas: [`backend/README.md`](backend/README.md) · [`frontend/README.md`](frontend/README.md)

## Arquitetura

```
Cliente (PWA)                          Servidor (API)
Next.js 16 + React 19                  FastAPI + SQLAlchemy async
Dexie.js → IndexedDB                   SQLite (aiosqlite, padrão) / Postgres
Service Worker (cache de assets)       JWT (access + refresh rotation)
        │  POST /api/sync (UUID, atualizado_em UTC, excluido)
        └──────────────────────────────▶
```

## Estrutura

```
backend/app/
├── core/            # config, database, security (JWT/bcrypt), init_db (seeds), exceptions
├── modules/         # auth · usuarios · contatos · sync · auditoria (models/repository/router/schemas por módulo)
├── api.py           # agrega os routers em /api
└── main.py
backend/migrations/  # Alembic

frontend/src/
├── app/page.tsx     # login, CRUD, sync, status offline
└── db/db.ts         # schema Dexie.js (LocalContato)

docker-compose.yml    # backend (8085) + frontend (8086), SQLite
```

## Modelo de Dados (`Contato`)

| Campo | Tipo | Observação |
|---|---|---|
| `id` | UUID (string) | gerado pelo **cliente** |
| `nome`, `telefone`, `email?` | string | `telefone` validado (min. 8 dígitos) |
| `tipo_numero` | `institucional` \| `publico` | enum |
| `atualizado_em` | datetime UTC | árbitro de conflito |
| `excluido` | bool | soft delete |
| `sincronizado` | bool (só no cliente) | nunca enviado ao servidor |

**Resolução de conflito (last-write-wins):** se o registro já existe no servidor, a versão do cliente só é aceita quando `cliente.atualizado_em > servidor.atualizado_em`; caso contrário é ignorada. Se não existe, é criado.

## Segurança e RBAC

- JWT access token (30 min) + refresh token com **rotação real** (reuso de token já rotacionado revoga todas as sessões do usuário).
- bcrypt assíncrono (thread pool). Soft delete em `contatos` e `usuarios`.
- Toda escrita gera um registro imutável em `audit_trail` (usuário, ação, tabela, dados modificados).
- Papéis: **GESTOR** (leitura/escrita de contatos + gestão de usuários) e **CONSULTOR** (somente leitura/sync).

Seeds (`RUN_SEEDS=1`): `gestor@hcfmb.unesp.br` / `gestor123` e `consultor@hcfmb.unesp.br` / `consultor123`.

## Endpoints

| Método | Rota | Papel | Descrição |
|---|---|---|---|
| POST | `/api/auth/login` | — | `{login, senha}` → tokens |
| POST | `/api/auth/refresh` | — | rotaciona tokens |
| POST | `/api/auth/logout` | — | revoga refresh token |
| GET | `/api/usuarios/me` | autenticado | usuário atual |
| GET/POST/PUT/DELETE | `/api/usuarios/...` | GESTOR | CRUD de usuários |
| GET | `/api/contatos/` | CONSULTOR+ | lista contatos ativos |
| POST | `/api/contatos/criar-editar` | GESTOR | cria/edita contato |
| POST | `/api/contatos/deletar` | GESTOR | soft delete (`{id}`) |
| POST | `/api/sync` | CONSULTOR+ | sync em lote, retorna `{sucesso, contatos_atualizados, error}` |

## Como Começar

**Docker Compose** (recomendado):
```bash
docker compose up -d --build
```
Backend em http://localhost:8085 (`/docs`), frontend em http://localhost:8086. Sobe com SQLite e seeds (`RUN_SEEDS=1`).

**Local:**
```bash
# backend
cd backend && python -m venv .venv && .\.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
RUN_SEEDS=1 uvicorn app.main:app --reload --port 8085

# frontend
cd frontend && npm install && npm run dev
```

## Variáveis de Ambiente (backend `.env`)

| Variável | Default | Descrição |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///:memory:` | SQLite ou Postgres (`asyncpg`) |
| `SECRET_KEY` | placeholder | assinatura JWT — **trocar em produção** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` / `REFRESH_TOKEN_EXPIRE_DAYS` | `30` / `7` | expiração dos tokens |
| `TOKEN_URL` | `/api/auth/login` | ajustar se montado como sub-app |
| `RUN_SEEDS` | `0` | cria tabelas + dados de demonstração |

## Testes

```bash
cd backend && pytest -v
```
Cobertura: autenticação/refresh, RBAC de contatos e usuários, sincronização/conflitos, validação de schemas. CI via `.github/workflows/ci.yml`.

## Deployment

`docker-compose.yml` atual usa SQLite (dev/staging). Para produção, trocar por Postgres (`DATABASE_URL=postgresql+asyncpg://...`, adicionar `asyncpg`), gerar `SECRET_KEY` seguro, restringir CORS (hoje `*` em `app/main.py`) e desativar `RUN_SEEDS`.

## Decisões de Arquitetura

| Decisão | Motivo |
|---|---|
| UUID gerado no cliente | evita conflito de PK em criação offline |
| Soft delete | propaga exclusão a clientes que ainda não sincronizaram |
| Timestamp UTC ponta a ponta | elimina ambiguidade de fuso horário |
| Refresh token rotativo | sessão resiliente + defesa contra roubo de token |
| Módulos por domínio (`app/modules/*`) | isola models/repository/router/schemas por contexto |

## Tecnologias

Backend: FastAPI 0.138 · SQLAlchemy 2.0 (async) · Pydantic 2.13 · python-jose · bcrypt · Alembic
Frontend: Next.js 16 (App Router) · React 19 · Dexie.js 4.4 · TypeScript 5 · @ducanh2912/next-pwa

---
*Desenvolvido pelo Estagiário Ricardo Florentino Rodrigues — Núcleo de Apoio à Gestão do HCFMB, Botucatu-SP*
