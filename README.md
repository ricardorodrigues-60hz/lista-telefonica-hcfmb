# 📞 Aciono Você — Lista Telefônica Hospitalar PWA Offline-First
### Hospital das Clínicas da Faculdade de Medicina de Botucatu (HCFMB · UNESP)

> **Sistema de alta criticidade** para gerenciamento de ramais e contatos institucionais, projetado para funcionar com plena capacidade mesmo em ausência de conexão de rede.

## Índice
- [Visão Geral](#-visão-geral-da-arquitetura)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Modelo de Dados](#-modelo-de-dados-e-contrato-de-sincronização)
- [Como Começar](#-como-começar)
- [Arquitetura Detalhada](#-arquitetura-offline-first-em-detalhes)
- [Segurança e Auditoria](#-segurança-e-auditoria)
- [Teste e Qualidade](#-testes-e-qualidade)
- [Deployment](#-deployment)

---

## 📐 Visão Geral da Arquitetura

O projeto adota uma arquitetura **Offline-First** com sincronização bidirecional baseada em UUID, timestamp UTC e Soft Delete. Os dados vivem simultaneamente no IndexedDB do navegador (via Dexie.js) e no banco SQLite do servidor (via aiosqlite + SQLAlchemy assíncrono). A resolução de conflitos é feita por comparação de `atualizado_em` — a modificação mais recente vence.

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENTE (PWA)                           │
│   Next.js 16 (App Router)  ·  React 19  ·  TypeScript           │
│   Dexie.js → IndexedDB (dados locais, sempre disponíveis)       │
│   Service Worker → Cache de assets estáticos                    │
└─────────────────────┬───────────────────────────────────────────┘
                      │  Sync via POST /api/contatos/sync
                      │  (payload: UUID + atualizado_em UTC + excluido)
┌─────────────────────▼───────────────────────────────────────────┐
│                     SERVIDOR (Backend API)                      │
│   FastAPI · Python 3.11 · Uvicorn                               │
│   SQLAlchemy 2 (async) · aiosqlite · Pydantic v2                │
│   JWT (Access + Refresh Token Rotation) · bcrypt                │
│   Trilha de Auditoria (AuditTrail) para todas as operações      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🗂️ Estrutura do Projeto

```
lista_telefonica_acionovoce/
├── backend/                     # API FastAPI
│   ├── app/
│   │   ├── core/
│   │   │   ├── auth.py          # JWT, OAuth2, require_gestor/require_consultor (RBAC)
│   │   │   ├── config.py        # Settings via pydantic_settings (.env)
│   │   │   ├── init_db.py       # Criação de tabelas e seed de dados (e-mail + senha)
│   │   │   └── passwords.py     # bcrypt async (thread pool)
│   │   ├── models/
│   │   │   └── models.py        # SQLAlchemy ORM: Usuario, RefreshToken, Contato, AuditTrail
│   │   ├── repositories/
│   │   │   ├── contatos.py      # ContatoRepository (CRUD + sincronização em lote)
│   │   │   └── usuarios.py      # UsuarioRepository + RefreshTokenRepository
│   │   ├── routers/
│   │   │   ├── auth.py          # /api/auth/login · /refresh · /logout
│   │   │   ├── contatos.py      # /api/contatos/ · /criar-editar · /deletar · /sync
│   │   │   └── usuarios.py      # /api/usuarios/ (CRUD, restrito a GESTOR)
│   │   ├── schemas/
│   │   │   ├── auth.py          # LoginRequest, TokenResponse, RefreshRequest, LogoutRequest
│   │   │   ├── contatos.py      # ContatoCreate, ContatoSync, SyncPayload, SyncResponse
│   │   │   └── usuarios.py      # UsuarioCreate, UsuarioUpdate, UsuarioResponse
│   │   ├── database.py          # Engine, session maker, Base declarativa
│   │   └── main.py              # FastAPI app, CORS, lifespan, montagem de rotas
│   ├── tests/                   # Suíte pytest (27 testes, 100% passando)
│   ├── Dockerfile               # Imagem de produção (app.main:app, sem --reload)
│   └── requirements.txt
│
├── frontend/                    # PWA Next.js
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx         # Aplicação principal (login, CRUD, sync, offline)
│   │   │   ├── layout.tsx
│   │   │   └── globals.css      # Design System — paleta HCFMB
│   │   └── db/
│   │       └── db.ts            # Dexie.js schema (LocalContato, AcionoVoceDB)
│   ├── public/                  # Manifest PWA, ícones
│   ├── Dockerfile               # Imagem de produção (npm run build + npm run start)
│   └── package.json
│
├── docker-compose.yml           # Orquestração completa (backend + frontend)
└── README.md
```

---

## 🔑 Modelo de Dados e Contrato de Sincronização

### Entidade `Contato` (Backend + Frontend)

| Campo | Tipo (Python) | Tipo (TypeScript) | Papel |
|---|---|---|---|
| `id` | `UUID` | `string` | Chave primária, gerada pelo **cliente** (UUIDv4) |
| `nome` | `str` | `string` | Nome do contato ou setor |
| `telefone` | `str` | `string` | Validado com regex (mín. 8 dígitos) |
| `email` | `Optional[EmailStr]` | `string?` | Opcional |
| `tipo_numero` | `TipoNumero` (Enum) | `'institucional' \| 'publico'` | Classificação do ramal |
| `atualizado_em` | `datetime` (UTC, timezone-aware) | `string` (ISO 8601) | **Árbitro de conflitos** na sincronização |
| `excluido` | `bool` | `boolean` | Flag de Soft Delete |
| `criado_em` | `datetime` (UTC) | — | Histórico de criação (servidor) |
| `sincronizado` | — | `boolean` | Estado local do Dexie.js (não vai ao servidor) |

### Regra de Resolução de Conflitos Offline

```
SE (contato já existe no servidor):
    SE (cliente.atualizado_em > servidor.atualizado_em):
        Cliente vence (envia alterações)
    SENÃO:
### Fluxo de Sincronização Bidirecional

1. **Operação Local (Offline):** Usuário cria/edita contato → Dexie.js + `sincronizado: false`
2. **Retorna Online:** Service Worker detecta → `window.online` event
3. **Coleta de Pendências:** Frontend agrupa todos `{ id, atualizado_em, excluido }` com `sincronizado: false`
4. **POST /api/contatos/sync:** Envia payload para servidor (JWT bearer token obrigatório)
5. **Comparação no Servidor:** 
   - Se `cliente.atualizado_em > servidor.atualizado_em` → cliente vence
   - Caso contrário → servidor vence, cliente recebe delta
6. **Persistência Local:** Frontend marca como `sincronizado: true` ou remove se `excluido: true`
7. **Notificação:** UI atualiza em tempo real via `useLiveQuery` do Dexie.js

### Camadas de Segurança

- **JWT Access Token:** curta duração (30 min default), renovado via `/api/auth/refresh`
- **Refresh Token com rotação real:** persistido (hash) em `refresh_tokens`; cada uso invalida o token anterior e reuso revoga todas as sessões
- **Senha Hash:** bcrypt assíncrono com salt automático
- **Soft Delete:** Dados nunca desaparecem (apenas `excluido: true`) — vale tanto para `contatos` quanto para `usuarios`
- **Audit Trail:** Cada operação registra `usuario_nome` (e-mail de quem executou), `acao`, `tabela`, `registro_id` e `dados_modificados` (JSON) de forma imutável
- **RBAC:** Dependências `require_gestor` (leitura+escrita) e `require_consultor` (qualquer papel autenticado)

---

## 🔐 Segurança e Auditoria

### Endpoints de Autenticação
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/api/auth/login` | Login com e-mail (`login`) + `senha` |
| `POST` | `/api/auth/refresh` | Rotaciona o par de tokens (revoga o refresh usado) |
| `POST` | `/api/auth/logout` | Revoga o refresh token da sessão atual |

### Endpoints de Contatos
| Método | Endpoint | Perfil | Descrição |
|--------|----------|--------|-----------|
| `GET` | `/api/contatos/` | Consultor+ | Lista paginada (sem soft-deletados) |
| `POST` | `/api/contatos/criar-editar` | Gestor | Cria ou atualiza contato |
| `DELETE` | `/api/contatos/deletar/{id}` | Gestor | Marca como `excluido: true` |
| `POST` | `/api/contatos/sync` | Consultor+ | Sincronização bidirecional offline |

### Trilha de Auditoria
Toda escrita (`criar`, `atualizar`, `deletar`, incluindo as originadas por `/sync`) registra em `audit_trail`:
```json
{
  "id": 42,
  "usuario_nome": "gestor@hcfmb.unesp.br",
  "acao": "EDITAR",
  "tabela": "contatos",
  "registro_id": "<contato_uuid>",
  "detalhes": "Contato Novo Nome (...) editado via painel online.",
  "dados_modificados": "{\"nome\": \"Novo Nome\", \"telefone\": \"...\"}",
  "criado_em": "2026-06-24T15:30:45Z"
}
```

---

## 🧪 Testes e Qualidade

- **Framework:** pytest + pytest-asyncio (11 testes, 100% cobertura de rotas)
- **Banco de Testes:** SQLite em memória para isolamento
- **Execução:** `cd backend && pytest -v`

Casos cobertos:
- ✅ Autenticação (login, refresh, tokens inválidos)
- ✅ CRUD de contatos (criar, ler, atualizar, deletar)
- ✅ Sincronização offline (conflitos, soft delete)
- ✅ Validação de schemas (email, telefone, enums)
- ✅ Permissõess (gestor vs consultor)

---

## 🔧 Desenvolvimento e Extensão

### Adicionar um Novo Campo em `Contato`

1. **Backend:** 
   - Edite `backend/app/models/models.py`
   - Execute `alembic revision --autogenerate -m "Descrição"` + `alembic upgrade head`
   - Atualize schema em `backend/app/schemas/contatos.py`

2. **Frontend:**
   - Edite interface `LocalContato` em `frontend/src/db/db.ts`
   - Atualize validação em `frontend/src/app/page.tsx`

3. **Testes:** Crie cenários em `backend/tests/test_contatos_endpoints.py`

### Integração num Portal Corporativo

O backend pode ser montado como sub-app FastAPI:

```python
from fastapi import FastAPI
from lista_telefonica.backend.app.main import app as lista_app

portal = FastAPI(title="Portal Hospitalar")
portal.mount("/lista-telefonica", lista_app)  # Monta em /lista-telefonica/*
```

---

## 🚢 Deployment

### Ambiente de Produção (docker-compose.yml)

```yaml
services:
  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql+asyncpg://user:pass@db:5432/lista_telefonica
      SECRET_KEY: <chave-secreta-production>
      ALGORITHM: HS256
    ports:
      - "8085:8000"

  frontend:
    build: ./frontend
    environment:
      NEXT_PUBLIC_API_URL: https://api.hospital.br/lista-telefonica
    ports:
      - "8086:3000"

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
- [ ] Variáveis de ambiente configuradas (`.env.production`)
- [ ] `SECRET_KEY` gerado com segurança (`openssl rand -hex 32`)
- [ ] SSL/TLS ativado (nginx reverso proxy)
- [ ] Backups automáticos do PostgreSQL
- [ ] Logs centralizados (ELK, DataDog, etc)
- [ ] Monitoramento de health checks (`/docs`)
- [ ] Rate limiting ativado nos routers
- [ ] CORS restrito a domínios confiáveis

---

## 🚀 Como Começar

### Pré-requisitos
- **Backend:** Python 3.11+, PostgreSQL 14+
- **Frontend:** Node.js 20+, npm 10+
- **Containerização:** Docker Desktop

### Inicialização Rápida (Docker Compose)

```bash
# 1. Clone o repositório
git clone <seu-repo> lista_telefonica_acionovoce
cd lista_telefonica_acionovoce

# 2. Inicie toda a stack
docker compose up -d --build

# 3. Acesse a aplicação
Frontend:   http://localhost:8086
Backend:    http://localhost:8085
Docs API:   http://localhost:8085/docs
```

**Credenciais de teste:**
- Usuário: `RI98234` (gestor com permissão de escrita)
- Usuário: `RI98235` (consultor com permissão de leitura)

### Desenvolvimento Local

#### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\activate
pip install -r requirements.txt

# Configure seu .env
cp .env.example .env  # Ajuste DATABASE_URL conforme necessário

# Migrações e seed
alembic upgrade head
python -m app.core.init_db

# Inicie o servidor (porta 8085)
uvicorn app.main:app --reload --port 8085
```

#### Frontend
```bash
cd frontend
npm install
npm run dev  # Servidor em http://localhost:8086
```

---

## ✨ Principais Features

| Feature | Descrição |
|---------|-----------|
| 🔌 **Offline-First** | Funciona sem internet; sincroniza automaticamente quando conectado |
| 🔐 **RBAC (Gestor/Consultor)** | Controle granular de permissões com auditoria completa |
| ⚡ **Async/Await** | Python 3.11 + FastAPI + SQLAlchemy 2.0 assíncrono |
| 📱 **PWA** | Installável como app nativo; Service Worker para cache de assets |
| 🎯 **Sincronização Inteligente** | Timestamp UTC + tipo_numero enum + soft delete |
| 📊 **Auditoria Imutável** | Trilha completa de quem fez o quê e quando |
| 🐳 **Container-Ready** | Docker Compose para dev, staging e produção |

---

## 📚 Arquitetura Offline-First em Detalhes

### Fluxo de Sincronização Bidirecional
        → Aceita a versão do cliente (vitória da edição offline mais recente)
    SENÃO:
        → Ignora (servidor tem a versão mais atual)
SENÃO:
    → Cria novo contato (criado inteiramente offline)
```

---

## 🛠️ Pré-requisitos

### Backend
- Python 3.11+
- `pip` para instalação de dependências
- Ambiente virtual recomendado (`.venv`)

### Frontend
- Node.js 20+
- npm 10+

---

## ⚡ Instalação e Execução Local

### 1. Clonar o repositório

```bash
git clone <URL_DO_REPOSITORIO>
cd lista_telefonica_acionovoce
```

### 2. Backend

```bash
cd backend

# Criar e ativar ambiente virtual
python -m venv .venv
.\.venv\Scripts\activate          # Windows
# source .venv/bin/activate       # Linux/macOS

# Instalar dependências
pip install -r requirements.txt

# Iniciar com seed de dados automático (cria tabelas + usuários padrão)
RUN_SEEDS=1 uvicorn app.main:app --host 0.0.0.0 --port 8085
# Windows (PowerShell):
$env:RUN_SEEDS="1"; uvicorn app.main:app --host 0.0.0.0 --port 8085
```

> A API estará disponível em: **http://localhost:8085**
> Documentação Swagger: **http://localhost:8085/docs**

### 3. Frontend

```bash
cd frontend

# Instalar dependências
npm install

# Iniciar servidor de desenvolvimento
npm run dev
```

> O PWA estará disponível em: **http://localhost:8086**

---

## 🐳 Execução com Docker Compose

```bash
# Na raiz do projeto — iniciar todos os serviços em background
docker compose up -d --build

# Verificar status dos containers
docker compose ps

# Acompanhar logs em tempo real
docker compose logs -f

# Parar e remover containers
docker compose down
```

| Serviço | Container | Porta |
|---|---|---|
| Backend API | `lista_backend_api` | `8085` |
| Frontend PWA | `lista_frontend_pwa` | `8086` |

---

## 🔐 Controle de Acesso (RBAC)

O sistema implementa dois papéis de usuário, protegidos por JWT com **rotação de Refresh Token**:

| Papel | Permissões |
|---|---|
| **GESTOR** | Visualizar, buscar, criar, editar e excluir contatos. Gerenciar usuários. |
| **CONSULTOR** | Somente visualizar e buscar contatos. |

### Contas Padrão (criadas automaticamente via `RUN_SEEDS=1`)

| Papel | E-mail | Senha |
|---|---|---|
| Gestor | `gestor@unesp.br` | `gestor123` |
| Consultor | `consultor@unesp.br` | `consultor123` |

> ⚠️ **Altere as senhas padrão antes de qualquer deploy em produção.**

### Endpoints de Autenticação

```
POST /api/auth/login    → { login, senha } → access_token + refresh_token + papel + nome
POST /api/auth/refresh  → Rotaciona tokens (revoga o antigo, emite novo par access + refresh)
POST /api/auth/logout   → Revoga o refresh token da sessão atual (204)
```

A rotação é real: cada `refresh_token` só pode ser usado uma vez. Reapresentá-lo depois de
já ter sido rotacionado revoga automaticamente todas as sessões do usuário (proteção contra
token roubado).

---

## 🔄 Endpoints de Sincronização

```
GET  /api/contatos/           → Lista todos os contatos ativos (qualquer papel autenticado)
POST /api/contatos/criar-editar → Cria ou edita um contato (somente GESTOR)
POST /api/contatos/deletar    → Soft Delete por UUID (somente GESTOR)
POST /api/contatos/sync       → Sincronização em lote offline → servidor (qualquer autenticado)
```

### Payload de Sincronização (`POST /api/contatos/sync`)

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
  ]
}
```

### Resposta de Sincronização

```json
{
  "sucesso": true,
  "contatos_atualizados": ["550e8400-e29b-41d4-a716-446655440000"]
}
```

> O campo de retorno é **`contatos_atualizados`** (lista de UUIDs confirmados). O frontend usa essa lista para marcar os registros locais do Dexie.js como `sincronizado: true`.

---

## 🧪 Testes Automatizados

O projeto mantém uma suíte de testes assíncronos com **pytest + httpx** cobrindo os principais fluxos:

```bash
cd backend
.\.venv\Scripts\python.exe -m pytest -v
```

| Arquivo de Teste | Cobertura |
|---|---|
| `test_auth_endpoints.py` | Login (sucesso/erro), rotação de refresh, reuso de token revogado, logout |
| `test_blocking_password_ops.py` | Verificação de bcrypt fora da thread principal |
| `test_contatos_endpoints.py` | Listagem, sincronização e RBAC de escrita (GESTOR vs CONSULTOR) |
| `test_schemas.py` | Validação Pydantic (telefone, e-mail, papel) |
| `test_usuarios_endpoints.py` | CRUD de usuários e RBAC (restrito a GESTOR) |

> **Resultado esperado:** `27 passed` ✅

---

## ⚙️ Variáveis de Ambiente

Crie um arquivo `.env` na pasta `backend/` com as seguintes variáveis:

```env
# URL do banco de dados (SQLite local ou PostgreSQL via asyncpg)
DATABASE_URL=sqlite+aiosqlite:///./lista.db

# Chave secreta para assinar os tokens JWT (alterar em produção!)
SECRET_KEY=sua-chave-secreta-muito-longa-e-aleatoria

# Algoritmo JWT
ALGORITHM=HS256

# Expiração do token de acesso (minutos)
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Expiração do refresh token (dias)
REFRESH_TOKEN_EXPIRE_DAYS=7

# URL do endpoint de autenticação (ajustar se montado como sub-app)
TOKEN_URL=/api/auth/login
```

> **`TOKEN_URL`** permite que a aplicação seja montada em qualquer prefixo de rota em servidores hospitalares existentes sem alterar o código-fonte.

---

## 🏥 Deploy como Sub-App em Portal Hospitalar

Se a API for montada como sub-aplicação em um servidor existente (ex: sob `/portal/aciono-voce`), basta definir no `.env`:

```env
TOKEN_URL=/portal/aciono-voce/api/auth/login
```

O Swagger UI utilizará automaticamente o caminho correto para autenticação.

---

## 🏗️ Decisões de Arquitetura

| Decisão | Justificativa |
|---|---|
| **UUID gerado no cliente** | Permite criar registros offline sem conflito de PK ao sincronizar |
| **Soft Delete (`excluido: true`)** | Garante propagação da exclusão para clientes offline que ainda não sincronizaram |
| **Timestamp UTC em toda a cadeia** | Elimina ambiguidade de fuso horário entre cliente (ISO 8601) e servidor |
| **Refresh Token com rotação** | Sessão resiliente em ambientes com conectividade intermitente |
| **bcrypt em thread pool** | Evita bloqueio do event loop assíncrono do FastAPI |
| **Trilha de Auditoria (AuditTrail)** | Rastreabilidade obrigatória em ambiente hospitalar |
| **`RUN_SEEDS` via env var** | Impede execução acidental de seeds em testes automatizados |

---

## 📦 Tecnologias

| Camada | Tecnologia | Versão |
|---|---|---|
| Backend | FastAPI | 0.110 |
| Backend | SQLAlchemy (async) | 2.0 |
| Backend | Pydantic | 2.6 |
| Backend | python-jose | 3.3 |
| Backend | bcrypt | 4.1 |
| Frontend | Next.js | 16.2 |
| Frontend | React | 19 |
| Frontend | Dexie.js | 4.4 |
| Frontend | TypeScript | 5 |
| Infra | Docker / Docker Compose | — |

---

*Desenvolvido pelo Estagiário Ricardo Florentino Rodrigues em parceria com o Núcleo de Apoio à Gestão do HCFMB, Botucatu-SP*