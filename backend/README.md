# 📞 Aciono Você — Backend (FastAPI)

[![CI](https://img.shields.io/badge/CI-pending-lightgrey)]

## Sumário
- [Visão geral](#visão-geral)
- [Arquitetura](#arquitetura)
- [Estrutura de Pastas](#estrutura-de-pastas)
- [Componentes Principais](#componentes-principais)
- [Fluxo de Autenticação](#fluxo-de-autenticação)
- [Banco de Dados](#banco-de-dados)
- [Sincronização Offline-First](#sincronização-offline-first)
- [Instalação](#instalação)
- [Execução](#execução)
- [Migrações](#migrações)
- [Seed de Dados](#seed-de-dados)
- [Endpoints da API](#endpoints-da-api)
- [Schema de Dados](#schema-de-dados)
- [Testes Automatizados](#testes-automatizados)
- [Troubleshooting](#troubleshooting)
- [CI/CD](#cicd)

## Visão geral
Esta API **FastAPI** fornece endpoints para gerenciamento de usuários e contatos hospitalares, suportando sincronização offline‑first, autenticação JWT e controle de acesso granular (RBAC). O backend foi projetado para ser integrado em outros sistemas através de um prefixo configurável (`API_BASE`) e segue as melhores práticas de segurança, escalabilidade e manutenibilidade.

## Arquitetura
A aplicação segue uma arquitetura em **camadas** (Layered Architecture) com separação clara entre responsabilidades:

```mermaid
graph TB
    subgraph Client["🖥️ Cliente (Browser/Mobile)"]
        A["Frontend/App Client"]
    end
    
    subgraph FastAPI["🚀 FastAPI Application"]
        subgraph Middleware["Middleware"]
            CORS["CORS Middleware<br/>(allow_origins, allow_methods)"]
            Auth["Authentication<br/>(JWT Token Validation)"]
        end
        
        subgraph Routers["📡 Routers/Endpoints"]
            AuthRouter["Auth Router<br/>(login, refresh)"]
            ContatosRouter["Contatos Router<br/>(CRUD, sync)"]
        end
        
        subgraph Services["🔧 Services & Core"]
            Config["Configuration<br/>(Settings via Pydantic)"]
            Database["Database Connection<br/>(AsyncSession)"]
            AuthService["Auth Service<br/>(JWT decode, user validation)"]
            Audit["Audit System<br/>(track changes)"]
        end
        
        subgraph Repositories["📦 Data Access Layer"]
            UserRepo["User Repository<br/>(query builder)"]
            ContatoRepo["Contato Repository<br/>(sync logic)"]
        end
    end
    
    subgraph DB["💾 Database"]
        PostgreSQL["PostgreSQL<br/>(or SQLite for dev)"]
        SQLAlchemy["SQLAlchemy ORM<br/>(async models)"]
    end
    
    Client -->|HTTP| CORS
    CORS -->|validate JWT| Auth
    Auth -->|route request| Routers
    Routers -->|inject deps| Services
    Services -->|query via| Repositories
    Repositories -->|ORM layer| SQLAlchemy
    SQLAlchemy -->|SQL| PostgreSQL
```

**Fluxo de Requisição:**
1. Cliente envia HTTP request com JWT no header `Authorization: Bearer <token>`
2. Middleware CORS valida origem
3. Decorator `@router.get(...)` recebe a requisição
4. FastAPI injeta dependências (`Depends(get_db)`, `Depends(get_current_user)`)
5. Handler executa lógica e usa repositórios para acessar dados
6. Repositório usa SQLAlchemy ORM para construir queries
7. Response é serializado via Pydantic `response_model` e retornado ao cliente

## Estrutura de Pastas

```
backend/
├── app/
│   ├── main.py                      # Entrada da aplicação FastAPI
│   ├── core/                        # Módulos de configuração e funcionalidades compartilhadas
│   │   ├── __init__.py
│   │   ├── config.py               # Variáveis de ambiente (Settings com Pydantic)
│   │   ├── database.py             # Configuração do banco (SQLAlchemy async)
│   │   ├── auth.py                 # Funções de dependência de autenticação (Depends)
│   │   ├── init_db.py              # Script de inicialização do banco de dados
│   │   ├── audit/
│   │   │   ├── __init__.py
│   │   │   └── models.py           # Modelo de auditoria (tracking de mudanças)
│   │   └── auth/
│   │       ├── __init__.py
│   │       └── service.py          # Lógica de JWT (encoding, decoding, validation)
│   │
│   └── modules/                     # Módulos de negócio (feature modules)
│       └── contatos/               # Módulo de contatos (exausão de funcionalidades)
│           ├── __init__.py
│           ├── models.py           # Modelos SQLAlchemy (ORM) para a tabela `contatos`
│           ├── schemas.py          # Pydantic schemas (request/response validation)
│           ├── repository.py       # Data access layer (queries, sync logic)
│           └── router.py           # Endpoints HTTP para contatos
│
├── migrations/                      # Alembic migrations (banco de dados versioning)
│   ├── env.py
│   ├── README
│   ├── script.py.mako
│   └── versions/                   # Arquivos de migração (.py)
│       └── a36a895e7353_transforma_usuarios_em_permissoes.py
│
├── tests/                           # Testes automatizados (pytest + pytest-asyncio)
│   ├── test_contatos_endpoints.py
│   └── test_schemas.py
│
├── scripts/                         # Scripts utilitários
│   └── debug_import.py
│
├── alembic.ini                      # Configuração do Alembic (DB migrations)
├── requirements.txt                 # Dependências Python (pip)
├── Dockerfile                       # Imagem Docker para deploy
└── README.md                        # Este arquivo
```

### Explicação de Cada Componente

#### `app/main.py` — Entrada da Aplicação
- Instancia `FastAPI()` com configurações de lifecycle
- Registra middleware CORS
- Inclui routers com prefixo `settings.API_BASE` (padrão: `/lista-telefonica/api`)
- Define endpoints raiz `/` e `{settings.API_BASE}`

#### `app/core/config.py` — Configuração Centralizada
- Usa `pydantic_settings.BaseSettings` para validação de env vars
- Lê arquivo `.env` automaticamente
- Define tipos e valores padrão para:
  - `DATABASE_URL`: conexão ao banco
  - `SECRET_KEY`: chave para assinar JWTs
  - `API_PORT`: porta de execução
  - `API_BASE`: prefixo de montagem da API (permite integração em outros sistemas)

#### `app/core/database.py` — Camada de Banco de Dados
- Configura `create_async_engine()` para suporte async/await
- Define `sessionmaker` para criar sessões de banco
- Função `get_db()` para injetar `AsyncSession` em endpoints (via `Depends()`)
- Suporta PostgreSQL (produção) ou SQLite (desenvolvimento)

#### `app/core/auth.py` — Dependências de Autenticação
- `get_current_user()`: extrai JWT do header, valida, retorna usuário autenticado
- `require_gestor()`: wrapper que valida se o papel do usuário é "gestor"
- Função `verify_token()`: decodifica JWT e retorna payload
- Integra-se com FastAPI via `Depends()` para injeção automática

#### `app/core/auth/service.py` — Lógica de JWT
- `UsuarioAutenticado`: dataclass com dados do usuário autenticado
- `encode_token()`: cria JWT access/refresh tokens com exp/iat claims
- `decode_token()`: valida assinatura e retorna payload
- Usa `PyJWT` com algoritmo HS256

#### `app/modules/contatos/models.py` — Modelos do Banco
- Classe `Contato` com `__tablename__ = "contatos"`
- Colunas: `id`, `nome`, `telefone`, `email`, `tipo_numero`, `atualizado_em`, `excluido`
- Usa SQLAlchemy ORM (async) com tipos compatíveis

#### `app/modules/contatos/schemas.py` — Esquemas Pydantic
- `ContatoResponse`: serializa contato para JSON (resposta do endpoint)
- `ContatoCreate`: valida dados de entrada para criar/editar contato
- `SyncPayload`: estrutura esperada no payload de sync offline
- Valida tipos, ranges, formatos (email, telefone, etc.)

#### `app/modules/contatos/repository.py` — Data Access Layer
- `ContatoRepository(db)`: classe com métodos para queries
- `listar_ativos()`: retorna contatos não marcados como excluídos
- `salvar_ou_atualizar()`: cria novo ou atualiza existente
- `sincronizar_lote_offline()`: lógica de merge/sync de dados offline
- Encapsula toda lógica SQL/ORM

#### `app/modules/contatos/router.py` — Endpoints HTTP
- `@router.get("/")`: lista contatos (autentica via JWT)
- `@router.post("/criar-editar")`: cria/atualiza (require_gestor)
- `@router.post("/deletar")`: soft-delete (marca `excluido=True`)
- `@router.post("/sync")`: sincroniza dados offline-first
- Cada endpoint injeta dependências (`db`, `usuario`, etc.)

#### `migrations/` — Versionamento do Banco
- Usa **Alembic** (manage de migrações para SQLAlchemy)
- Cada arquivo em `versions/` representa uma mudança (upgrade/downgrade)
- `alembic revision --autogenerate -m "msg"` cria nova migração
- `alembic upgrade head` aplica todas as pendentes

#### `tests/` — Testes Automatizados
- Usa `pytest` + `pytest-asyncio` + `pytest-cov`
- Testa endpoints (status code, JSON response)
- Testa esquemas (validação Pydantic)
- Banco SQLite em memória (`:memory:`) para testes rápidos

## Componentes Principais

### FastAPI
- **Framework web assíncrono** moderno e rápido
- Validação automática via **Pydantic** (request/response)
- Geração automática de docs: `/docs` (Swagger UI) e `/redoc`
- Suporte nativo a async/await (I/O não-bloqueante)
- Injeção de dependências (Depends) muito robusta

### SQLAlchemy (Async)
- **ORM** (Object-Relational Mapping) para Python
- Suporte assíncrono (via `asyncio`)
- Queries type-safe e abstração de SQL direto
- Funciona com PostgreSQL, SQLite, MySQL, etc.
- Migrations via Alembic (versionamento do schema)

### Pydantic
- **Validação de dados** em runtime
- Serialização JSON automática (modelos → JSON)
- Type hints integradas (Python 3.8+)
- Mensagens de erro claras para dados inválidos
- Schemas para request (ContatoCreate) e response (ContatoResponse)

### JWT (JSON Web Tokens)
- **Autenticação stateless** (servidor não armazena sessão)
- Token assinado com `SECRET_KEY` (HS256)
- Claims: `sub` (user_id), `exp` (expiração), `iat` (issued at)
- Refresh token para renovação sem re-autenticar
- Via biblioteca `PyJWT`

## Fluxo de Autenticação

```
┌─────────────────────────────────────────────────────────────┐
│ Fluxo de Login                                               │
└─────────────────────────────────────────────────────────────┘

1. Cliente POST /lista-telefonica/api/auth/login
   {
     "usuario_id_externo": "RI98234",
     "senha": "senha123"
   }

2. Backend valida credenciais contra banco de dados
   (compara hash da senha)

3. Se válido, gera dois tokens:
   - access_token (JWT curta duração, 30 min padrão)
   - refresh_token (JWT longa duração, 7 dias padrão)

4. Retorna ao cliente:
   {
     "access_token": "eyJhbGc...",
     "refresh_token": "eyJhbGc...",
     "token_type": "bearer"
   }

┌──────────────────────────────────────────────────────────────┐
│ Fluxo de Requisição Autenticada                               │
└──────────────────────────────────────────────────────────────┘

1. Cliente guarda tokens (localStorage, sessionStorage, etc)

2. Próxima requisição, cliente envia:
   GET /lista-telefonica/api/contatos/
   Authorization: Bearer eyJhbGc...

3. FastAPI middleware extrai token do header

4. Função get_current_user() decodifica JWT:
   - Valida assinatura com SECRET_KEY
   - Valida exp (expiração)
   - Retorna payload (usuario_id_externo, papel, iat)

5. Se válido, injeta UsuarioAutenticado no handler da rota
   Se inválido, retorna 401 Unauthorized

6. Handler executa com usuário autenticado

7. Response é enviado com status 200

┌──────────────────────────────────────────────────────────────┐
│ Fluxo de Refresh Token                                        │
└──────────────────────────────────────────────────────────────┘

1. Access token expirou (status 401)

2. Cliente POST /lista-telefonica/api/auth/refresh
   {
     "refresh_token": "eyJhbGc..."
   }

3. Backend valida refresh_token

4. Se válido, emite novo access_token

5. Cliente atualiza token em memória e retenta operação
```

## Banco de Dados

### Estratégia de Conexão
- **Assíncrona**: usa `asyncpg` (driver PostgreSQL async)
- **Pool de Conexões**: reutiliza conexões abertas
- **Sessão por Requisição**: cada requisição HTTP tem sua própria `AsyncSession`

### Modelos Principais

#### Tabela `usuarios`
```python
# Valores de exemplo
usuario_id_externo: "RI98234"  # ID vindo de sistema externo
papel: "gestor"                 # "gestor" ou "consultor"
senha_hash: "bcrypt:..."        # Hash bcrypt da senha
criado_em: datetime
atualizado_em: datetime
```

#### Tabela `contatos`
```python
id: UUID                        # PK, gerado automaticamente
nome: str                       # Nome do contato
telefone: str                   # Formato (XX) XXXXX-XXXX
email: str                      # Email para validação
tipo_numero: str               # "institucional" ou "publico"
atualizado_em: datetime        # Última modificação
excluido: bool                 # Soft-delete (não remove da DB)
criado_por: str                # Quem criou (usuario_id_externo)
atualizado_por: str            # Quem atualizou
```

### Soft Delete vs Hard Delete
- **Soft Delete**: marca `excluido = True` (padrão desta API)
- **Vantagem**: permite auditoria, recuperação de dados, GDPR compliance
- **Queries automáticas**: `listar_ativos()` filtra `where excluido = False`

## Sincronização Offline-First

### Conceito
A aplicação suporta que clientes (mobile/web) trabalhem offline e depois sincronizem dados com o servidor quando conectado.

### Fluxo

```
┌─────────────────────────────────────────────────────────────┐
│ Fase 1: Trabalho Offline (sem conexão)                       │
└─────────────────────────────────────────────────────────────┘

1. App mobile guarda dados em IndexedDB/SQLite local
2. Usuário criou/editou/deletou contatos
3. App mantém timestamp local (atualizado_em)

┌──────────────────────────────────────────────────────────────┐
│ Fase 2: Sincronização (conexão restaurada)                    │
└──────────────────────────────────────────────────────────────┘

1. Client envia POST /api/contatos/sync
   Payload:
   {
     "contatos": [
       {"id": "...", "nome": "...", "atualizado_em": "2024-01-01T10:00:00Z"},
       ...
     ]
   }

2. Backend recebe lote de contatos

3. Para cada contato:
   - Se novo (id não existe): INSERT
   - Se existente:
     - Se client.atualizado_em > server.atualizado_em: UPDATE
     - Se server.atualizado_em > client.atualizado_em: client é old, mantém server (conflict resolution)
   - Se marcado deletado: executar soft-delete

4. Retorna:
   {
     "sucesso": true,
     "contatos_atualizados": ["id1", "id2", ...]
   }

5. Client atualiza seu banco local com IDs confirmadas
```

### Estratégia de Conflito Resolver
**Last-Write-Wins (LWW)**: o timestamp mais recente prevalece. Dados analiticamente verdadeiros caso timestamps estejam corretos.

## Instalação
| Pré‑requisito | Versão | Descrição |
|---|---|---|
| Python | 3.11+ | Runtime Python moderno com suporte async/await |
| PostgreSQL | 14+ | Banco de dados recomendado (produção) |
| virtualenv | any | Isolamento de dependências Python |
| Git | any | Controle de versão (clonar o repo) |

### Passo 1: Clonar Repositório e Navegar
```bash
git clone <repo-url>
cd lista_telefonica_acionovoce/backend
```

### Passo 2: Criar Ambiente Virtual
```bash
# Criar ambiente virtual
python -m venv .venv

# Ativar no PowerShell (Windows)
.\.venv\Scripts\Activate.ps1

# Ativar no bash/zsh (Linux/Mac)
source .venv/bin/activate
```

### Passo 3: Instalar Dependências
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Dependências principais (em `requirements.txt`):
- **fastapi**: framework web
- **sqlalchemy**: ORM assíncrono
- **asyncpg**: driver PostgreSQL async
- **pydantic**: validação de dados
- **pydantic-settings**: gerenciar variáveis de ambiente
- **alembic**: migrações de banco
- **python-jose**: criptografia de JWT
- **bcrypt**: hash de senhas
- **pytest**: framework de testes
- **pytest-asyncio**: suporte a testes async

### Passo 4: Configurar Variáveis de Ambiente
Crie arquivo `.env` na raiz de `backend/` com:

```env
# Banco de Dados
DATABASE_URL=sqlite+aiosqlite:///./lista.db
# ou para PostgreSQL:
# DATABASE_URL=postgresql+asyncpg://postgres:senha@localhost:5432/lista_telefonica

# Segurança JWT
SECRET_KEY=uma-chave-super-secreta-de-minimo-32-caracteres-aleatorios-segura
ALGORITHM=HS256

# Expiração de Tokens
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Autenticação
TOKEN_URL=/lista-telefonica/api/auth/login

# Servidor
API_PORT=8085

# Montagem da API (permite integração em outros sistemas)
API_BASE=/lista-telefonica/api
```

**⚠️ Segurança**: em produção, gere `SECRET_KEY` com:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Passo 5: Inicializar Banco de Dados
```bash
# Criar tabelas a partir dos modelos
alembic upgrade head

# (Opcional) Popular com dados de exemplo
python -m app.core.init_db
```

Pronto! Backend configurado.

## Execução

### Desenvolvimento (Auto-reload)
```bash
# Com reload automático (detecta mudanças de código)
uvicorn app.main:app --reload --port 8085

# Acessa em: http://localhost:8085/docs
```

**Logs úteis**:
```
INFO:     Uvicorn running on http://127.0.0.1:8085
INFO:     Application startup complete
```

### Produção (Multi-worker)
```bash
# Com múltiplos workers (mais performance)
uvicorn app.main:app --workers 4 --port 8085 --host 0.0.0.0

# --host 0.0.0.0: aceita requisições de qualquer IP
# --workers 4: usa 4 processos Python (ajuste conforme CPU)
```

### Docker Compose
```bash
# Suba backend + banco de dados em containers
docker compose up -d --build backend

# Logs em tempo real
docker compose logs -f backend

# Parar serviços
docker compose down
```

Arquivo `docker-compose.yml` gerencia:
- Backend FastAPI (porta 8085)
- PostgreSQL (porta 5432)
- Volumes para dados persistentes

## Migrações

### Conceito
Alembic gerencia mudanças no schema do banco de dados. Cada migração é um arquivo Python versionado que pode ser aplicado (`upgrade`) ou desfeito (`downgrade`).

### Criar Nova Migração
Após modificar um modelo SQLAlchemy:
```bash
# Auto-detecta mudanças nos modelos
alembic revision --autogenerate -m "adiciona coluna status em contatos"

# Cria arquivo em migrations/versions/XXX_adiciona_coluna_status_em_contatos.py
```

### Aplicar Migrações
```bash
# Aplica todas as migrações pendentes
alembic upgrade head

# Aplica específica
alembic upgrade <arquivo>

# Ver histórico
alembic history

# Ver status atual
alembic current
```

### Desfazer Migrações
```bash
# Desfaz a última migração aplicada
alembic downgrade -1

# Desfaz até específica
alembic downgrade <arquivo>
```

## Seed de Dados

### Criar Dados Iniciais
```bash
python -m app.core.init_db
```

### O que é Criado
- **Usuários de teste**:
  - `RI98234` (papel: "gestor", senha: "senha123")
  - `RI98235` (papel: "consultor", senha: "senha123")
- **Contatos de exemplo**: 5 contatos hospitalares

**Nota**: Útil para desenvolvimento. Em produção, use outro processo de seed.

## Endpoints da API

### Autenticação

#### Login
```http
POST /lista-telefonica/api/auth/login
Content-Type: application/json

{
  "usuario_id_externo": "RI98234",
  "senha": "senha123"
}
```

**Resposta (200 OK)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Possíveis erros**:
- `401 Unauthorized`: credenciais inválidas
- `422 Unprocessable Entity`: formato inválido

#### Refresh Token
```http
POST /lista-telefonica/api/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGc..."
}
```

**Resposta (200 OK)**:
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

### Contatos

#### Listar Contatos
```http
GET /lista-telefonica/api/contatos/
Authorization: Bearer eyJhbGc...
```

**Resposta (200 OK)**:
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "nome": "Hospital Central",
    "telefone": "(14) 3811-0000",
    "email": "contato@hospital.com",
    "tipo_numero": "institucional",
    "atualizado_em": "2024-01-15T10:30:00Z"
  }
]
```

#### Criar/Editar Contato
```http
POST /lista-telefonica/api/contatos/criar-editar
Authorization: Bearer eyJhbGc...
Content-Type: application/json

{
  "nome": "Hospital da Paz",
  "telefone": "(11) 3245-9876",
  "email": "paz@hospital.com",
  "tipo_numero": "publico"
}
```

**Nota**: Requer papel "gestor"

**Resposta (200 OK)**: Contato criado/atualizado com id gerado.

#### Deletar Contato (Soft Delete)
```http
POST /lista-telefonica/api/contatos/deletar
Authorization: Bearer eyJhbGc...
Content-Type: application/json

{
  "id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Nota**: Mark como `excluido = True`, não remove do banco.

#### Sincronização Offline-First
```http
POST /lista-telefonica/api/contatos/sync
Authorization: Bearer eyJhbGc...
Content-Type: application/json

{
  "contatos": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "nome": "Hospital Atualizado",
      "telefone": "(14) 3811-0001",
      "email": "novo@hospital.com",
      "tipo_numero": "institucional",
      "atualizado_em": "2024-01-15T15:00:00Z"
    }
  ]
}
```

**Resposta (200 OK)**:
```json
{
  "sucesso": true,
  "contatos_atualizados": [
    "550e8400-e29b-41d4-a716-446655440000"
  ]
}
```

## Schema de Dados

### Enums

#### TipoNumero
```python
class TipoNumero(str, Enum):
    institucional = "institucional"  # Números de hospitais, clínicas
    publico = "publico"              # Números abertos ao público
```

#### Papel
```python
class Papel(str, Enum):
    consultor = "consultor"  # Apenas lê dados
    gestor = "gestor"        # Cria, edita, deleta contatos
```

### Modelos Pydantic

#### ContatoResponse (Resource de Resposta)
```python
class ContatoResponse(BaseModel):
    id: UUID
    nome: str
    telefone: str
    email: str
    tipo_numero: TipoNumero
    atualizado_em: datetime
```

#### ContatoCreate (Request de Entrada)
```python
class ContatoCreate(BaseModel):
    nome: str                   # 1-255 caracteres
    telefone: str               # Validado com regex
    email: str                  # Email válido
    tipo_numero: TipoNumero    # "institucional" ou "publico"
```

#### SyncPayload (Sincronização Offline)
```python
class SyncPayload(BaseModel):
    contatos: List[ContatoSync]

class ContatoSync(BaseModel):
    id: UUID
    nome: str
    telefone: str
    email: str
    tipo_numero: TipoNumero
    atualizado_em: datetime
```

#### UsuarioAutenticado (Dados do Token Decodificado)
```python
class UsuarioAutenticado:
    usuario_id_externo: str
    papel: Papel
    iat: int  # issued at (timestamp Unix)
```

## Testes Automatizados

### Rodando Testes

#### Todos os testes
```bash
cd backend
.venv\Scripts\pytest -q
```

#### Com verbosidade
```bash
.venv\Scripts\pytest -v
```

#### Teste específico
```bash
.venv\Scripts\pytest tests/test_contatos_endpoints.py -v
```

#### Com cobertura de código
```bash
.venv\Scripts\pytest --cov=app --cov-report=html

# Abre relatório HTML em htmlcov/index.html
```

### Configuração de Testes

#### Variáveis de Ambiente para CI
Para rodар os testes na pipeline CI (GitHub Actions), configure:
```yaml
env:
  API_BASE: "/api"  # Testes esperam /api/... (não /lista-telefonica/api/...)
```

Em desenvolvimento local, você pode:
```bash
# PowerShell
$env:API_BASE = "/api"
.\.venv\Scripts\pytest -q

# Bash/Zsh
API_BASE=/api pytest -q
```

#### Banco de Dados de Testes
- Usa **SQLite em memória** (`:memory:`)
- Rápido e isolado (cada teste tem seu próprio banco)
- Definido em `core/config.py` (DATABASE_URL padrão)

### Estrutura de Testes

```
tests/
├── test_contatos_endpoints.py   # Testa rotas HTTP, status codes, JSON responses
└── test_schemas.py              # Testa validação Pydantic dos esquemas
```

### Exemplo de Teste
```python
@pytest.mark.asyncio
async def test_get_contatos_and_sync(monkeypatch):
    # Setup: Mock do ContatoRepository
    import app.modules.contatos.router as contatos_mod
    monkeypatch.setattr(contatos_mod, "ContatoRepository", lambda db: FakeRepo(db))
    
    # Setup: Override dependency de autenticação
    from app.core.auth import get_current_user
    app.dependency_overrides[get_current_user] = lambda: UsuarioAutenticado(...)
    
    # Executa: Faz requisição HTTP simulada
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/api/contatos/")
    
    # Assert: Valida resposta
    assert r.status_code == 200
    assert isinstance(r.json(), list)
```

## Troubleshooting

### ModuleNotFoundError: 'app'
**Problema**: Ao rodar `python -m app.core.init_db` ou pytest.

**Solução**: 
```bash
cd backend  # Certifique-se de estar na pasta backend/
```

### Database not found
**Problema**: `Error: database "lista_telefonica" does not exist`

**Solução**:
```bash
# Criar banco PostgreSQL
createdb lista_telefonica

# Ou ajustar DATABASE_URL em .env
DATABASE_URL=sqlite+aiosqlite:///./lista.db
```

### Token expirado (401 Unauthorized)
**Problema**: Requests retornam 401 Unauthorized.

**Solução**:
```bash
# Use o refresh token para obter novo access_token
POST /lista-telefonica/api/auth/refresh
{"refresh_token": "..."}
```

### CORS errors (browser retorna erro CORS)
**Problema**: Front-end não consegue fazer requisições cross-origin.

**Solução**: Ajustar `CORSMiddleware` em `app/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Não usar "*" em produção
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### API_BASE não está sendo lido de .env
**Problema**: Backend segue usando `/lista-telefonica/api` mesmo após mudar `.env`.

**Solução**:
```bash
# Reinicie o servidor (uvicorn lê .env ao iniciar)
```

### Testes falhando com 404 em `/api/contatos`
**Problema**: 
```
assert 404 == 200
```

**Solução**: Rode com `API_BASE=/api`:
```bash
$env:API_BASE = "/api"
.\.venv\Scripts\pytest -q
```

## CI/CD

### GitHub Actions
Pipeline em `.github/workflows/ci.yml` executa:
1. **Checkout** do código
2. **Setup Python 3.11**
3. **Install dependencies** de `backend/requirements.txt`
4. **Run backend tests** com `API_BASE=/api`

**Sempre que**:
- Push em branch `beta-01`
- Pull request para `main`, `master`, `beta-0`

**Logs de sucesso**:
```
✅ Run backend tests: 1 passed
```

**Para debug localmente**:
```bash
#Simule o que CI faz
$env:API_BASE = "/api"
python -m pytest -q
```
