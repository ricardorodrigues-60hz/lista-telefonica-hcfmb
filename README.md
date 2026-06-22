# 📞 Aciono Você — Lista Telefônica Hospitalar PWA Offline-First
### Hospital das Clínicas da Faculdade de Medicina de Botucatu (HCFMB · UNESP)

> **Sistema de alta criticidade** para gerenciamento de ramais e contatos institucionais, projetado para funcionar com plena capacidade mesmo em ausência de conexão de rede.

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
│   │   │   ├── auth.py          # JWT, OAuth2, require_gestor (RBAC)
│   │   │   ├── config.py        # Settings via pydantic_settings (.env)
│   │   │   ├── init_db.py       # Criação de tabelas e seed de dados
│   │   │   └── passwords.py     # bcrypt async (thread pool)
│   │   ├── models/
│   │   │   └── models.py        # SQLAlchemy ORM: Usuario, Contato, AuditTrail
│   │   ├── repositories/
│   │   │   ├── contatos.py      # ContatoRepository (CRUD + sincronização em lote)
│   │   │   └── usuario.py       # UsuarioRepository
│   │   ├── routers/
│   │   │   ├── auth.py          # /api/auth/login · /api/auth/refresh
│   │   │   ├── contatos.py      # /api/contatos/ · /criar-editar · /deletar · /sync
│   │   │   └── usuarios.py      # /api/usuarios/
│   │   ├── schemas/
│   │   │   ├── auth.py          # LoginRequest, TokenResponse, RefreshRequest
│   │   │   ├── contatos.py      # ContatoCreate, ContatoSync, SyncPayload, SyncResponse
│   │   │   └── usuarios.py      # UsuarioCreate, UsuarioResponse
│   │   ├── database.py          # Engine, session maker, Base declarativa
│   │   └── main.py              # FastAPI app, CORS, lifespan, montagem de rotas
│   ├── tests/                   # Suíte pytest (11 testes, 100% passando)
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
POST /api/auth/login    → Retorna access_token + refresh_token
POST /api/auth/refresh  → Rotaciona tokens (novo par access + refresh)
```

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
| `test_auth_endpoints.py` | Login e refresh de token |
| `test_blocking_password_ops.py` | Verificação de bcrypt fora da thread principal |
| `test_contatos_endpoints.py` | Listagem e sincronização de contatos |
| `test_schemas.py` | Validação Pydantic (telefone, papel, SecretStr) |
| `test_usuarios_endpoints.py` | CRUD de usuários e RBAC |

> **Resultado esperado:** `11 passed` ✅

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