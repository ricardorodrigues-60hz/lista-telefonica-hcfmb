# 📞 Aciono Você — Lista Telefônica Hospitalar PWA Offline-First
### Hospital das Clínicas da Faculdade de Medicina de Botucatu (HCFMB · UNESP)

> **Sistema de alta criticidade** para gerenciamento de ramais e contatos institucionais, projetado para funcionar com plena capacidade mesmo em ausência de conexão de rede.

## Índice
- [Visão Geral da Arquitetura](#-visão-geral-da-arquitetura)
- [Estrutura do Projeto](#️-estrutura-do-projeto)
- [Modelo de Dados e Sincronização](#-modelo-de-dados-e-contrato-de-sincronização)
- [Segurança, RBAC e Auditoria](#-segurança-rbac-e-auditoria)
- [Endpoints da API](#-endpoints-da-api)
- [Como Começar](#-como-começar)
- [Variáveis de Ambiente](#️-variáveis-de-ambiente)
- [Testes Automatizados](#-testes-automatizados)
- [Desenvolvimento e Extensão](#-desenvolvimento-e-extensão)
- [Deployment](#-deployment)
- [Decisões de Arquitetura](#️-decisões-de-arquitetura)
- [Tecnologias](#-tecnologias)

---

## 📐 Visão Geral da Arquitetura

O projeto adota uma arquitetura **Offline-First** com sincronização bidirecional baseada em UUID, timestamp UTC e Soft Delete. Os dados vivem simultaneamente no IndexedDB do navegador (via Dexie.js) e no banco do servidor (SQLite via `aiosqlite` por padrão, com SQLAlchemy assíncrono). A resolução de conflitos é feita por comparação de `atualizado_em` — a modificação mais recente vence (*last-write-wins*).

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENTE (PWA)                           │
│   Next.js 16 (App Router)  ·  React 19  ·  TypeScript           │
│   Dexie.js → IndexedDB (dados locais, sempre disponíveis)       │
│   Service Worker (@ducanh2912/next-pwa) → cache de assets       │
└─────────────────────┬───────────────────────────────────────────┘
                      │  Sync via POST /api/sync
                      │  (payload: UUID + atualizado_em UTC + excluido)
┌─────────────────────▼───────────────────────────────────────────┐
│                     SERVIDOR (Backend API)                      │
│   FastAPI · Python 3.11 · Uvicorn                               │
│   SQLAlchemy 2 (async) · aiosqlite · Pydantic v2                │
│   JWT (Access + Refresh Token Rotation) · bcrypt                │
│   Trilha de Auditoria (AuditTrail) para todas as operações      │
└─────────────────────────────────────────────────────────────────┘
```

> O backend está pronto para PostgreSQL em produção (basta trocar `DATABASE_URL` para uma URL `postgresql+asyncpg://...` e adicionar `asyncpg` às dependências); por padrão, tanto localmente quanto no `docker-compose.yml`, usa-se SQLite.

Para detalhes de implementação de cada camada, veja também:
- [`backend/README.md`](backend/README.md) — arquitetura modular, endpoints e troubleshooting do backend.
- [`frontend/README.md`](frontend/README.md) — lógica de sincronização offline, PWA e schema do Dexie.js.

---

## 🗂️ Estrutura do Projeto

```
lista_telefonica_acionovoce/
├── backend/                         # API FastAPI
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py            # Settings via pydantic_settings (.env)
│   │   │   ├── database.py          # Engine assíncrono, session maker, Base declarativa
│   │   │   ├── exceptions.py        # Exceções de domínio + exception handlers
│   │   │   ├── init_db.py           # Criação de tabelas e seed (usuários + contatos demo)
│   │   │   ├── logging.py           # Configuração de logging da aplicação
│   │   │   └── security.py          # JWT, bcrypt assíncrono (thread pool), oauth2_scheme
│   │   ├── modules/                 # Um módulo de domínio por pasta (models/repository/router/schemas)
│   │   │   ├── auth/                # Login, refresh (rotação), logout, RBAC (require_gestor/require_consultor)
│   │   │   ├── usuarios/            # CRUD de usuários (restrito a GESTOR)
│   │   │   ├── contatos/            # CRUD de contatos + soft delete
│   │   │   ├── sync/                # Sincronização offline-first (last-write-wins)
│   │   │   └── auditoria/           # AuditTrail (models + repository)
│   │   ├── api.py                   # Agrega os routers de todos os módulos em api_router
│   │   └── main.py                  # FastAPI app, CORS, lifespan (seeds), montagem de rotas
│   ├── migrations/                  # Alembic (versions/, env.py)
│   ├── tests/                       # Suíte pytest + pytest-asyncio
│   ├── alembic.ini
│   ├── Dockerfile                   # Imagem de produção (uvicorn app.main:app, porta 8085)
│   └── requirements.txt
│
├── frontend/                        # PWA Next.js
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx             # Aplicação principal (login, CRUD, sync, offline)
│   │   │   ├── layout.tsx
│   │   │   └── globals.css          # Design System — paleta HCFMB
│   │   └── db/
│   │       └── db.ts                # Dexie.js schema (LocalContato, AcionoVoceDB)
│   ├── public/                      # Manifest PWA, Service Worker (sw.js), ícones
│   ├── Dockerfile                   # Imagem de produção (npm run build + npm run start, porta 8086)
│   └── package.json
│
├── .github/workflows/ci.yml         # CI: roda a suíte pytest do backend a cada push/PR
├── docker-compose.yml               # Orquestração local (backend + frontend, SQLite)
└── README.md
```

---

## 🔑 Modelo de Dados e Contrato de Sincronização

### Entidade `Contato` (Backend + Frontend)

| Campo | Tipo (Python) | Tipo (TypeScript) | Papel |
|---|---|---|---|
| `id` | `str` (UUID) | `string` | Chave primária, gerada pelo **cliente** (UUIDv4) |
| `nome` | `str` | `string` | Nome do contato ou setor |
| `telefone` | `str` | `string` | Validado com regex (mín. 8 dígitos) |
| `email` | `Optional[EmailStr]` | `string?` | Opcional |
| `tipo_numero` | `TipoNumero` (Enum: `institucional`/`publico`) | `'institucional' \| 'publico'` | Classificação do ramal |
| `atualizado_em` | `datetime` (UTC, timezone-aware) | `string` (ISO 8601) | **Árbitro de conflitos** na sincronização |
| `excluido` | `bool` | `boolean` | Flag de Soft Delete |
| `criado_em` | `datetime` (UTC) | — | Histórico de criação (servidor) |
| `sincronizado` | — | `boolean` | Estado local do Dexie.js (nunca é enviado ao servidor) |

### Regra de Resolução de Conflitos Offline (last-write-wins)

```
SE (contato já existe no servidor):
    SE (cliente.atualizado_em > servidor.atualizado_em):
        → Aceita a versão do cliente (vitória da edição offline mais recente)
    SENÃO:
        → Ignora (servidor já tem a versão mais atual)
SENÃO:
    → Cria novo contato (registro criado inteiramente offline)
```

### Fluxo de Sincronização Bidirecional

1. **Operação Local (Offline):** Usuário cria/edita contato → Dexie.js + `sincronizado: false`
2. **Retorna Online:** listener de `window.online` dispara a sincronização
3. **Coleta de Pendências:** Frontend agrupa todos `{ id, nome, telefone, email, tipo_numero, atualizado_em, excluido }` com `sincronizado: false`
4. **POST /api/sync:** Envia o payload para o servidor (JWT bearer token obrigatório — qualquer papel autenticado)
5. **Comparação no Servidor:** `SyncService` aplica a regra last-write-wins descrita acima, registrando auditoria de cada alteração aceita
6. **Persistência Local:** Frontend marca como `sincronizado: true` usando a lista `contatos_atualizados` da resposta
7. **Notificação:** UI atualiza em tempo real via `useLiveQuery` do Dexie.js

---

## 🔐 Segurança, RBAC e Auditoria

O sistema implementa dois papéis de usuário, protegidos por JWT com **rotação real de Refresh Token**:

| Papel | Permissões |
|---|---|
| **GESTOR** | Visualizar, criar, editar e excluir contatos; gerenciar usuários |
| **CONSULTOR** | Somente visualizar contatos e sincronizar |

- **JWT Access Token:** curta duração (`ACCESS_TOKEN_EXPIRE_MINUTES`, 30 min por padrão), renovado via `/api/auth/refresh`
- **Refresh Token com rotação real:** persistido (hash) em `refresh_tokens`; cada uso invalida o token anterior. Reapresentar um token já rotacionado/revogado indica possível roubo de token e **revoga automaticamente todas as sessões do usuário**
- **Senha Hash:** bcrypt assíncrono (executado em thread pool para não bloquear o event loop)
- **Soft Delete:** dados nunca desaparecem (apenas `excluido: true`) — vale tanto para `contatos` quanto para `usuarios`
- **Audit Trail (`audit_trail`):** cada operação de escrita (via painel ou via `/sync`) registra `usuario_nome`, `acao`, `tabela`, `registro_id`, `detalhes` e `dados_modificados` (JSON) de forma imutável
- **RBAC:** dependências `require_gestor` e `require_consultor` (qualquer papel autenticado), definidas em `app/modules/auth/service.py`

### Contas Padrão (criadas automaticamente via `RUN_SEEDS=1`)

| Papel | E-mail | Senha |
|---|---|---|
| Gestor | `gestor@hcfmb.unesp.br` | `gestor123` |
| Consultor | `consultor@hcfmb.unesp.br` | `consultor123` |

> ⚠️ **Altere as senhas padrão antes de qualquer deploy em produção.** O seed também é desativado por padrão (`RUN_SEEDS=0`) para não rodar acidentalmente em testes/CI.

---

## 📡 Endpoints da API

### Autenticação (`/api/auth`)
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/api/auth/login` | Login com `login` (e-mail) + `senha` → access + refresh token |
| `POST` | `/api/auth/refresh` | Rotaciona o par de tokens (revoga o refresh usado) |
| `POST` | `/api/auth/logout` | Revoga o refresh token da sessão atual (204) |

### Usuários (`/api/usuarios`) — restrito a GESTOR, exceto `/me`
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/api/usuarios/me` | Dados do próprio usuário autenticado |
| `GET` | `/api/usuarios/` | Lista usuários ativos |
| `GET` | `/api/usuarios/{id}` | Obtém um usuário por ID |
| `POST` | `/api/usuarios/` | Cria um novo usuário |
| `PUT` | `/api/usuarios/{id}` | Atualiza nome/papel/senha |
| `DELETE` | `/api/usuarios/{id}` | Soft delete (não é possível excluir o próprio usuário) |

### Contatos (`/api/contatos`)
| Método | Endpoint | Perfil | Descrição |
|--------|----------|--------|-----------|
| `GET` | `/api/contatos/` | Consultor+ | Lista todos os contatos ativos |
| `POST` | `/api/contatos/criar-editar` | Gestor | Cria ou atualiza um contato |
| `POST` | `/api/contatos/deletar` | Gestor | Soft delete via `{ "id": "<uuid>" }` no corpo |

### Sincronização (`/api/sync`)
| Método | Endpoint | Perfil | Descrição |
|--------|----------|--------|-----------|
| `POST` | `/api/sync` | Consultor+ | Sincronização bidirecional em lote (offline → servidor) |

**Payload:**
```json
{
  "contatos": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "nome": "Portaria Principal",
      "telefone": "(14) 3811-1500",
      "email": "portaria@hcfmb.unesp.br",
      "tipo_numero": "publico",
      "atualizado_em": "2026-06-22T12:00:00Z",
      "excluido": false
    }
  ],
  "ultima_sincronizacao": null
}
```

**Resposta:**
```json
{
  "sucesso": true,
  "contatos_atualizados": ["550e8400-e29b-41d4-a716-446655440000"],
  "error": null
}
```

> O campo de retorno é **`contatos_atualizados`** (lista de UUIDs confirmados). O frontend usa essa lista para marcar os registros locais do Dexie.js como `sincronizado: true`.

---

## 🚀 Como Começar

### Pré-requisitos
- **Backend:** Python 3.11+
- **Frontend:** Node.js 20+, npm 10+
- **Containerização (opcional):** Docker Desktop

### Inicialização Rápida (Docker Compose)

```bash
git clone <seu-repo> lista_telefonica_acionovoce
cd lista_telefonica_acionovoce

docker compose up -d --build
```

| Serviço | Container | Porta | URL |
|---|---|---|---|
| Backend API | `lista_backend_api` | `8085` | http://localhost:8085 (docs em `/docs`) |
| Frontend PWA | `lista_frontend_pwa` | `8086` | http://localhost:8086 |

O `docker-compose.yml` já sobe o backend com `RUN_SEEDS=1` (cria tabelas e as contas padrão acima) e usa SQLite (`sqlite+aiosqlite:///./lista.db`) — não é necessário nenhum banco externo para rodar localmente.

```bash
docker compose ps           # status dos containers
docker compose logs -f      # logs em tempo real
docker compose down         # parar e remover containers
```

### Desenvolvimento Local

#### Backend
```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate          # Windows
# source .venv/bin/activate       # Linux/macOS

pip install -r requirements.txt

# (Opcional) crie um .env — veja a seção "Variáveis de Ambiente"

# Aplique as migrações Alembic
alembic upgrade head

# Inicie o servidor com seed automático de dados
# Linux/macOS:
RUN_SEEDS=1 uvicorn app.main:app --reload --host 0.0.0.0 --port 8085
# Windows (PowerShell):
$env:RUN_SEEDS="1"; uvicorn app.main:app --reload --port 8085
```

> API em **http://localhost:8085** · Swagger em **http://localhost:8085/docs**

#### Frontend
```bash
cd frontend
npm install
npm run dev   # http://localhost:8086 (usa NEXT_PUBLIC_API_URL, default http://localhost:8085)
```

---

## ⚙️ Variáveis de Ambiente

Configuráveis via `.env` na pasta `backend/` (lidas por `app/core/config.py`):

| Variável | Default | Descrição |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///:memory:` | URL do banco (SQLite local ou PostgreSQL via `asyncpg`) |
| `SECRET_KEY` | chave de exemplo (**alterar em produção**) | Chave para assinar os tokens JWT |
| `ALGORITHM` | `HS256` | Algoritmo JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Expiração do access token |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Expiração do refresh token |
| `TOKEN_URL` | `/api/auth/login` | Caminho usado pelo Swagger para autenticação (ajustar se montado como sub-app) |
| `RUN_SEEDS` | `0` | Se `1`, cria tabelas e contas/contatos de demonstração no startup |

No frontend, `NEXT_PUBLIC_API_URL` (lida em `frontend/src/app/page.tsx`) define a URL base da API.

---

## 🧪 Testes Automatizados

```bash
cd backend
pytest -v
```

- **Framework:** pytest + pytest-asyncio + httpx (`ASGITransport`), banco SQLite em memória
- **CI:** `.github/workflows/ci.yml` executa a suíte a cada push/PR

| Arquivo de Teste | Cobertura |
|---|---|
| `test_auth_endpoints.py` | Login (sucesso/erro), rotação de refresh, reuso de token revogado, logout |
| `test_blocking_password_ops.py` | Garante que hash/verificação de senha roda fora da thread principal |
| `test_contatos_endpoints.py` | Listagem, criação e RBAC de escrita (GESTOR vs CONSULTOR) |
| `test_schemas.py` | Validação Pydantic (telefone, e-mail, papel) |
| `test_sync_endpoints.py` | Sincronização: criação offline, conflito last-write-wins, autenticação obrigatória |
| `test_usuarios_endpoints.py` | CRUD de usuários e RBAC (restrito a GESTOR) |

---

## 🔧 Desenvolvimento e Extensão

### Adicionar um Novo Campo em `Contato`

1. **Backend:**
   - Edite `backend/app/modules/contatos/models.py` (coluna SQLAlchemy)
   - Atualize os schemas em `backend/app/modules/contatos/schemas.py` (e `backend/app/modules/sync/schemas.py`, se o campo participa da sincronização)
   - Gere e aplique a migração: `alembic revision --autogenerate -m "Descrição"` + `alembic upgrade head`

2. **Frontend:**
   - Edite a interface `LocalContato` em `frontend/src/db/db.ts` (e crie uma nova `db.version(n)` se alterar índices)
   - Atualize formulário/validação em `frontend/src/app/page.tsx`

3. **Testes:** cubra o novo campo em `backend/tests/test_contatos_endpoints.py` e/ou `test_sync_endpoints.py`

### Integração num Portal Corporativo

O backend pode ser montado como sub-app FastAPI:

```python
from fastapi import FastAPI
from lista_telefonica.backend.app.main import app as lista_app

portal = FastAPI(title="Portal Hospitalar")
portal.mount("/lista-telefonica", lista_app)  # Monta em /lista-telefonica/*
```

Ajuste `TOKEN_URL` no `.env` para o caminho completo (ex: `/lista-telefonica/api/auth/login`), garantindo que o Swagger UI autentique corretamente.

---

## 🚢 Deployment

### `docker-compose.yml` (ambiente local/atual)

```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8085:8085"
    environment:
      - DATABASE_URL=sqlite+aiosqlite:///./lista.db
      - RUN_SEEDS=1

  frontend:
    build: ./frontend
    ports:
      - "8086:8086"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8085
    depends_on:
      - backend
```

### Evoluindo para Produção (PostgreSQL)

Para produção recomenda-se substituir o SQLite por PostgreSQL, adicionando `asyncpg` a `backend/requirements.txt` e um serviço `db` ao compose:

```yaml
  backend:
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/lista_telefonica
      - SECRET_KEY=<chave-secreta-de-produção>
      - RUN_SEEDS=0

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: lista_telefonica
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - pgdata:/var/lib/postgresql/data
```

**Checklist de Produção:**
- [ ] `SECRET_KEY` gerado com segurança (`openssl rand -hex 32`) e fora do controle de versão
- [ ] `RUN_SEEDS=0` (ou senhas padrão alteradas antes de habilitar)
- [ ] Banco migrado com `alembic upgrade head` (evitar depender de `create_all` em produção)
- [ ] SSL/TLS ativado (proxy reverso)
- [ ] CORS restrito a domínios confiáveis (hoje `allow_origins=["*"]` em `app/main.py`)
- [ ] Backups automáticos do banco de dados
- [ ] Logs centralizados e monitoramento de health check (`/docs`)

---

## 🏗️ Decisões de Arquitetura

| Decisão | Justificativa |
|---|---|
| **UUID gerado no cliente** | Permite criar registros offline sem conflito de PK ao sincronizar |
| **Soft Delete (`excluido: true`)** | Garante propagação da exclusão para clientes offline que ainda não sincronizaram |
| **Timestamp UTC em toda a cadeia** | Elimina ambiguidade de fuso horário entre cliente (ISO 8601) e servidor |
| **Refresh Token com rotação** | Sessão resiliente em ambientes com conectividade intermitente, com defesa contra reuso de token |
| **bcrypt em thread pool** | Evita bloqueio do event loop assíncrono do FastAPI |
| **Trilha de Auditoria (AuditTrail)** | Rastreabilidade obrigatória em ambiente hospitalar |
| **Arquitetura modular (`app/modules/*`)** | Cada domínio (auth, usuarios, contatos, sync, auditoria) é autocontido (models/repository/router/schemas) |
| **`RUN_SEEDS` via env var** | Impede execução acidental de seeds em testes automatizados |

---

## 📦 Tecnologias

| Camada | Tecnologia | Versão |
|---|---|---|
| Backend | FastAPI | 0.138 |
| Backend | SQLAlchemy (async) | 2.0 |
| Backend | Pydantic / pydantic-settings | 2.13 / 2.14 |
| Backend | python-jose | 3.3 |
| Backend | bcrypt | 4.1 |
| Backend | Alembic | migrações em `backend/migrations` |
| Frontend | Next.js | 16.2 (App Router) |
| Frontend | React | 19.2 |
| Frontend | Dexie.js / dexie-react-hooks | 4.4 |
| Frontend | TypeScript | 5 |
| Frontend | @ducanh2912/next-pwa | 10.2 |
| Infra | Docker / Docker Compose | — |
| CI | GitHub Actions (`.github/workflows/ci.yml`) | — |

---

*Desenvolvido pelo Estagiário Ricardo Florentino Rodrigues em parceria com o Núcleo de Apoio à Gestão do HCFMB, Botucatu-SP*
