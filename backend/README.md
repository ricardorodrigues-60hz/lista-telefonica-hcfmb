# 📞 Aciono Você — Backend (FastAPI)

> **API de alta performáce** para sincronização offline-first de contatos hospitalares, com controle de acesso granular (RBAC) e auditoria completa de operações.

Este módulo constitui o backend do sistema **Aciono Você**, projetado especificamente para operar sob o padrão **Offline-First**, fornecendo endpoints de sincronização bidirecional, autenticação JWT e trilha de auditoria imutável.

## Índice
- [Arquitetura do Sistema](#-arquitetura-do-sistema)
- [Componentes Principais](#-componentes-principais)
- [Autenticação e Autorização](#-autenticação-e-autorização)
- [Endpoints da API](#-endpoints-da-api)
- [Schema de Dados](#-schema-de-dados)
- [Instalação e Execução](#-instalação-e-execução)
- [Testes Automatizados](#-testes-automatizados)
- [Troubleshooting](#-troubleshooting)

---

## 🏛️ Arquitetura do Sistema

A aplicação adota **organização por módulos de domínio** (auth, usuarios, contatos, sync, auditoria), cada um com suas próprias camadas internas, mais um `core/` com as preocupações transversais (config, banco, segurança, exceções, logging):

```
app/
├── main.py                 # bootstrap do FastAPI, CORS, exception handlers
├── api.py                  # agrega o router de cada módulo em /api
├── core/
│   ├── config.py           # Settings (Pydantic Settings)
│   ├── database.py         # engine/Session assíncronos, Base declarativa
│   ├── security.py         # primitivas de JWT e hashing de senha (bcrypt)
│   ├── exceptions.py        # exceções de domínio + handlers HTTP
│   ├── logging.py          # configuração centralizada de logging
│   └── init_db.py          # seed de dados de desenvolvimento
└── modules/
    ├── auth/                # models(RefreshToken), schemas, repository, service (login/refresh/RBAC), router
    ├── usuarios/            # models(Usuario), schemas, repository, router (CRUD simples, sem service)
    ├── contatos/            # models(Contato), schemas, repository, router (CRUD simples, sem service)
    ├── sync/                # schemas, service (resolução de conflitos last-write-wins), router
    └── auditoria/           # models(AuditTrail), repository, schemas (usado pelos demais módulos)
```

Fluxo de uma requisição: **Router (HTTP)** → **Service** (quando há lógica não-trivial: auth, sync) → **Repository** (persistência/SQLAlchemy) → **Models** (ORM) → **PostgreSQL** (async via `asyncpg`).

### Benefícios da Arquitetura

1. **Alta coesão / baixo acoplamento:** cada módulo agrupa tudo que muda junto (schemas, models, repository, router do mesmo domínio).
2. **Testabilidade:** Repositories e Services podem ser mockados; testes usam banco em memória (SQLite).
3. **Escalabilidade:** novos domínios entram como novos módulos, sem inflar pastas técnicas compartilhadas.
4. **Auditoria:** toda escrita relevante passa pelo `AuditoriaRepository`, centralizando a trilha imutável.
5. **Segurança:** RBAC via dependências `require_gestor` e `require_consultor` (módulo `auth`).

---

## 🔧 Componentes Principais

### 1. **Routers** (`modules/*/router.py`)
Definem os endpoints HTTP e validam entrada/saída via Pydantic schemas. Nunca acessam o banco diretamente:

- **`auth/router.py`:** Login (e-mail + senha), refresh com rotação, logout
- **`usuarios/router.py`:** Gerenciamento de usuários (CRUD, restrito a GESTOR)
- **`contatos/router.py`:** CRUD de contatos (leitura para CONSULTOR/GESTOR, escrita restrita a GESTOR)
- **`sync/router.py`:** Endpoint `POST /api/sync` de sincronização offline-first

### 2. **Services** (`modules/*/service.py`)
Usados apenas onde há lógica não-trivial (login/RBAC e resolução de conflitos):

- **`auth/service.py` (`AuthService`):** autentica, emite/rotaciona tokens, logout; expõe `get_current_user`, `require_gestor`, `require_consultor`
- **`sync/service.py` (`SyncService`):** decide, por contato, se a versão offline vence o registro do servidor (last-write-wins)

### 3. **Repositories** (`modules/*/repository.py`)
Encapsulam lógica de acesso a dados (CRUD, joins, persistência), sem regra de negócio:

- **`contatos/repository.py` (`ContatoRepository`):** CRUD + soft delete + métodos de persistência usados pelo `SyncService`
- **`usuarios/repository.py` (`UsuarioRepository`):** busca por e-mail, hashing de senha (bcrypt), CRUD de usuários
- **`auth/repository.py` (`RefreshTokenRepository`):** persistência de sessões (hash SHA-256 do token), rotação e revogação
- **`auditoria/repository.py` (`AuditoriaRepository`):** ponto único de escrita da trilha de auditoria, usado pelos demais repositories

### 4. **Models** (`modules/*/models.py`)
Definem tabelas SQLAlchemy, uma por módulo de domínio:

```python
class Usuario(Base):
    """Usuário autenticado por e-mail + senha, com papel RBAC"""
    __tablename__ = "usuarios"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_novo_uuid)
    nome: Mapped[str]
    email: Mapped[str] = mapped_column(unique=True, index=True)
    senha_hash: Mapped[str]
    papel: Mapped[str]  # "GESTOR" ou "CONSULTOR"
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    excluido: Mapped[bool] = mapped_column(default=False)

class RefreshToken(Base):
    """Sessão de refresh token (hash), habilitando rotação e revogação real"""
    __tablename__ = "refresh_tokens"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_novo_uuid)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id"))
    token_hash: Mapped[str] = mapped_column(unique=True, index=True)
    expira_em: Mapped[datetime]
    revogado: Mapped[bool] = mapped_column(default=False)
    substituido_por_id: Mapped[Optional[str]]  # aponta para o token que o substituiu na rotação

class Contato(Base):
    """Contato ou ramal hospitalar"""
    __tablename__ = "contatos"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID gerado no cliente
    nome: Mapped[str]
    telefone: Mapped[str]
    email: Mapped[Optional[str]]
    tipo_numero: Mapped[str]  # "institucional" ou "publico"
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    excluido: Mapped[bool] = mapped_column(default=False)

class AuditTrail(Base):
    """Trilha imutável de todas as operações de escrita (contatos e usuários)"""
    __tablename__ = "audit_trail"
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_nome: Mapped[str]  # e-mail de quem executou a ação
    acao: Mapped[str]  # "CRIAR", "EDITAR", "EXCLUIR", "CRIAR_SYNC"...
    tabela: Mapped[str]  # "contatos" ou "usuarios"
    registro_id: Mapped[Optional[str]]
    detalhes: Mapped[str]
    dados_modificados: Mapped[Optional[str]]  # JSON serializado com o diff
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())
```

### 5. **Schemas** (`modules/*/schemas.py`)
Validação com Pydantic v2, um arquivo por módulo:

```python
# modules/contatos/schemas.py
class ContatoCreate(ContatoBase):
    """Entrada para criar/atualizar contato via painel"""
    id: UUID  # Gerado pelo cliente

# modules/sync/schemas.py
class ContatoSync(BaseModel):
    """Item individual do lote de sincronização offline"""
    id: UUID
    nome: str
    telefone: str
    email: Optional[EmailStr] = None
    tipo_numero: TipoNumero
    atualizado_em: datetime  # normalizado para UTC
    excluido: bool = False

class SyncPayload(BaseModel):
    contatos: list[ContatoSync]
    ultima_sincronizacao: Optional[datetime] = None

class SyncResponse(BaseModel):
    sucesso: bool
    contatos_atualizados: list[UUID]
    error: Optional[list[str]] = None
```

### 6. **Core** (`core/`)
Preocupações transversais, sem conhecimento de nenhum domínio específico:

- **`security.py`:** JWT (access/refresh) e hashing de senha (bcrypt com thread pool)
- **`config.py`:** Variáveis de ambiente via Pydantic Settings
- **`database.py`:** engine/Session assíncronos e `Base` declarativa
- **`exceptions.py`:** exceções de domínio (`CredenciaisInvalidasError`, `TokenInvalidoError`, etc.) e handlers HTTP
- **`logging.py`:** configuração centralizada de logging
- **`init_db.py`:** seed de dados de desenvolvimento

Regras de RBAC (`get_current_user`, `require_gestor`, `require_consultor`) vivem em `modules/auth/service.py`, pois dependem do modelo `Usuario` — mantendo `core/` livre de acoplamento com módulos de domínio.

---

## 🔐 Autenticação e Autorização

### Fluxo de Autenticação

```mermaid
graph LR
    A[Cliente] -->|POST /api/auth/login| B[Endpoint Login]
    B -->|Valida e-mail + senha bcrypt| C{Credenciais OK?}
    C -->|Sim| D["JWT: Access (30min) + Refresh (7d)"]
    C -->|Não| E[401 Unauthorized]
    D -->|Retorna ao cliente| A
    A -->|Authorization: Bearer &lt;token&gt;| F[Endpoint Protegido]
    F -->|Verifica JWT| G{Token válido?}
    G -->|Sim| H[Executa endpoint]
    G -->|Não| I[401 ou 403]
```

O refresh token é persistido (via hash) em `refresh_tokens`. Cada uso em `POST /api/auth/refresh` **rotaciona** a sessão: o token antigo é revogado e um novo par é emitido. Reapresentar um token já rotacionado revoga automaticamente todas as sessões do usuário (indica possível token roubado). `POST /api/auth/logout` revoga o refresh token da sessão atual.

### Middleware de RBAC

```python
# Aplicado nas rotas
@router.post("/criar-editar", dependencies=[Depends(require_gestor)])
async def criar_editar_contato(...):
    """Apenas GESTOR pode escrever"""
    pass

@router.get("/", dependencies=[Depends(require_consultor)])
async def listar_contatos(...):
    """GESTOR ou CONSULTOR podem ler"""
    pass
```

**Escopo de Papéis:**

| Papel | Leitura | Escrita de contatos | Sincronização | Gestão de usuários |
|-------|---------|----------------------|----------------|---------------------|
| `CONSULTOR` | ✅ | ❌ | ✅ | ❌ |
| `GESTOR` | ✅ | ✅ | ✅ | ✅ |

---

## 📡 Endpoints da API

### Autenticação

#### `POST /api/auth/login`
```bash
curl -X POST http://localhost:8085/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login": "gestor@hcfmb.unesp.br", "senha": "gestor123"}'
```

**Response (200):**
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "papel": "GESTOR",
  "nome": "Gestor HCFMB"
}
```

#### `POST /api/auth/refresh`
Rotaciona o par de tokens (o refresh token usado é revogado e substituído):
```bash
curl -X POST http://localhost:8085/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJhbGc..."}'
```
Resposta (200): mesmo formato do login, com um novo `access_token` e `refresh_token`.
Se o `refresh_token` apresentado já tiver sido rotacionado/revogado, retorna **401**.

#### `POST /api/auth/logout`
```bash
curl -X POST http://localhost:8085/api/auth/logout \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJhbGc..."}'
```
Revoga a sessão (refresh token) atual. Resposta: **204 No Content**.

### Usuários (Requer GESTOR, exceto `/me`)

```
GET    /api/usuarios/me         → Perfil do usuário autenticado (qualquer papel)
GET    /api/usuarios/           → Lista usuários ativos
GET    /api/usuarios/{id}       → Obtém um usuário por ID
POST   /api/usuarios/           → Cria usuário (nome, email, senha, papel)
PUT    /api/usuarios/{id}       → Atualiza nome/papel/senha
DELETE /api/usuarios/{id}       → Soft delete (não permite autoexclusão)
```

### Contatos

#### `GET /api/contatos/` (Paginado)
```bash
curl -H "Authorization: Bearer <token>" \
  'http://localhost:8085/api/contatos/?skip=0&limit=10&tipo_numero=institucional'
```

**Response (200):**
```json
{
  "total": 42,
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "nome": "Ramal Recepção",
      "telefone": "2137",
      "email": "recep@hcfmb.br",
      "tipo_numero": "institucional",
      "atualizado_em": "2026-06-24T15:30:45Z",
      "criado_em": "2026-06-20T10:00:00Z"
    }
  ]
}
```

#### `POST /api/contatos/criar-editar` (Requer GESTOR)
```bash
curl -X POST http://localhost:8085/api/contatos/criar-editar \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "nome": "Novo Ramal",
    "telefone": "2138",
    "email": "novo@hcfmb.br",
    "tipo_numero": "institucional",
    "atualizado_em": "2026-06-24T15:35:00Z"
  }'
```

#### `DELETE /api/contatos/deletar/{id}` (Requer GESTOR)
```bash
curl -X DELETE http://localhost:8085/api/contatos/deletar/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer <token>"
```

Marca contato como `excluido: true` (soft delete).

### Sincronização (módulo `sync`)

#### `POST /api/sync` (Sincronização Offline)
Endpoint crítico para a estratégia offline-first. Implementado no módulo `sync` (não em `contatos`), pois envolve resolução de conflito — responsabilidade do `SyncService`:

```bash
curl -X POST http://localhost:8085/api/sync \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "contatos": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "nome": "Ramal Recepção",
        "telefone": "2137",
        "email": "recep@hcfmb.br",
        "tipo_numero": "institucional",
        "atualizado_em": "2026-06-24T15:35:00Z",
        "excluido": false
      }
    ]
  }'
```

**Response (200):**
```json
{
  "sucesso": true,
  "contatos_atualizados": ["550e8400-e29b-41d4-a716-446655440000"],
  "error": null
}
```

**Regra de Sincronização (last-write-wins, em `SyncService.sincronizar`):**
- Se o contato não existe no servidor → cria com o `id` e timestamp vindos do cliente
- Se existe e `cliente.atualizado_em > servidor.atualizado_em` → aceita a alteração do cliente (inclusive `excluido`)
- Se existe e a alteração do cliente for mais antiga → descarta silenciosamente (o servidor mantém a versão mais recente)
- Cada item processado é auditado (`CRIAR_SYNC`, `EDITAR_SYNC` ou `EXCLUIR_SYNC`) via `AuditoriaRepository`

> ⚠️ Este endpoint mudou de `POST /api/contatos/sync` para `POST /api/sync` na reorganização em módulos — o que, na verdade, corrige uma inconsistência pré-existente com o frontend, que já chamava `POST /api/sync`.

---

## 📊 Schema de Dados

### Enum `TipoNumero`
```python
class TipoNumero(str, Enum):
    institucional = "institucional"  # Ramal interno
    publico = "publico"              # Número público
```

### Papel do usuário
```python
PapelUsuario = Literal["GESTOR", "CONSULTOR"]
# CONSULTOR: apenas leitura + sync
# GESTOR:    leitura + escrita de contatos + gestão de usuários
```

---
Para viabilizar a integração transparente no ecossistema do hospital, o app expõe o parâmetro `TOKEN_URL` no `config.py` e parametriza o `OAuth2PasswordBearer` dinamicamente. Desta forma, ele pode ser montado dentro de outro app FastAPI:

```python
from fastapi import FastAPI
from app.main import app as lista_telefonica_app

parent_app = FastAPI(title="Portal Hospitalar Integrado")

# Montando o módulo de lista telefônica
parent_app.mount("/lista-telefonica", lista_telefonica_app)

# Agora rotas estão em:
# POST /lista-telefonica/api/auth/login
# GET /lista-telefonica/api/contatos/
# etc.
```

---

## 🚀 Instalação e Execução

### Pré-requisitos
- Python 3.11+
- PostgreSQL 14+ ou SQLite 3 (desenvolvimento)
- pip ou conda

### Execução Local com Virtualenv

#### 1. Prepare o Ambiente

```bash
cd backend

# Crie virtualenv
python -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\activate

# Instale dependências
pip install -r requirements.txt
```

#### 2. Configure Variáveis de Ambiente

Crie um arquivo `.env` na raiz de `backend/`:

```env
# Database PostgreSQL
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/lista_telefonica

# Ou SQLite (desenvolvimento local)
# DATABASE_URL=sqlite+aiosqlite:///./lista_telefonica.db

# JWT
SECRET_KEY=sua_chave_secreta_muito_longa_aqui_minimo_32_caracteres
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# API
TOKEN_URL=/api/auth/login
API_PORT=8085
ENVIRONMENT=development
```

#### 3. Inicie o Banco de Dados

Se usar PostgreSQL local:
```bash
# Linux/macOS
createdb lista_telefonica

# Ou via Docker
docker run -d --name pg_lista \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=lista_telefonica \
  -p 5432:5432 \
  postgres:15-alpine
```

#### 4. Execute Migrações (Alembic)

```bash
# Gere nova migração quando alterar models
alembic revision --autogenerate -m "Descrição da mudança"

# Aplique todas as pendentes
alembic upgrade head

# Inspecione versão atual
alembic current

# Reverta uma versão (apenas dev!)
# alembic downgrade -1
```

#### 5. Crie Dados Iniciais (Seed)

```bash
python -m app.core.init_db
```

Cria:
- 2 usuários de teste (`RI98234` gestor, `RI98235` consultor)
- 5 contatos hospitalares de exemplo

#### 6. Inicie o Servidor

```bash
# Com reload automático (desenvolvimento)
uvicorn app.main:app --reload --port 8085 --host 0.0.0.0

# Sem reload (staging/produção)
uvicorn app.main:app --port 8085 --workers 4
```

Servidor em: **http://localhost:8085**
Docs Swagger: **http://localhost:8085/docs**
Docs ReDoc: **http://localhost:8085/redoc**

### Execução Completa via Docker Compose

Do diretório raiz do projeto:

```bash
docker compose up -d --build

# Aguarde ~10s pela inicialização do banco
docker compose logs -f backend

# Teste a API
curl http://localhost:8085/docs
```

---

## 🧪 Testes Automatizados

A suíte de testes utiliza **pytest** + **pytest-asyncio** com **SQLite em memória** para isolamento completo.

### Rodar Testes

```bash
cd backend

# Todos os testes com resumo
pytest -v

# Apenas um arquivo
pytest tests/test_contatos_endpoints.py -v

# Apenas uma função
pytest tests/test_auth_endpoints.py::test_login_usuario_inexistente -v

# Com cobertura
pytest --cov=app tests/ --cov-report=html
```

### Testes Disponíveis

| Arquivo | Testes |
|---------|--------|
| `test_auth_endpoints.py` | Login (sucesso/erro), rotação de refresh, reuso de token revogado, logout |
| `test_contatos_endpoints.py` | Listagem, sync e RBAC de escrita (GESTOR vs CONSULTOR) |
| `test_blocking_password_ops.py` | Hash/verificação bcrypt fora da thread principal |
| `test_schemas.py` | Validação Pydantic (telefone, e-mail, papel) |
| `test_usuarios_endpoints.py` | CRUD de usuários e RBAC (GESTOR only) |

> **Resultado esperado:** `27 passed` ✅

### Exemplo: Teste de Sincronização

```python
@pytest.mark.asyncio
async def test_sync_conflito_timestamp():
    """Verifica last-write-wins baseado em atualizado_em"""
    client = TestClient(app)
    
    # 1. Login como gestor
    response = client.post("/api/auth/login", json={
        "login": "gestor@hcfmb.unesp.br",
        "senha": "gestor123"
    })
    token = response.json()["access_token"]
    
    # 2. Sincroniza com contato local
    response = client.post("/api/contatos/sync", 
        headers={"Authorization": f"Bearer {token}"},
        json={
            "contatos": [{
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "atualizado_em": "2026-06-24T16:00:00Z",  # Mais recente
                "excluido": False
            }]
        }
    )
    
    assert response.status_code == 200
    assert response.json()["contatos_atualizados"] == []  # Cliente venceu
```

---

## 🔧 Troubleshooting

### ❌ "ModuleNotFoundError: No module named 'app'"

**Solução:** Certifique-se de estar na pasta `backend/` e execute com `python -m`:
```bash
python -m app.core.init_db
python -m pytest tests/
```

### ❌ "asyncpg.exceptions.InvalidCatalogNameError: database 'lista_telefonica' does not exist"

**Solução:** Crie o banco PostgreSQL primeiro:
```bash
createdb lista_telefonica

# Ou use SQLite para dev (mude DATABASE_URL no .env)
```

### ❌ "SQLALCHEMY_SILENCE_UBER_WARNING not recognized"

**Solução:** Atualize SQLAlchemy:
```bash
pip install --upgrade "sqlalchemy>=2.0"
```

### ❌ Token expirado (401 Unauthorized)

**Solução:** Faça refresh do token:
```bash
curl -X POST http://localhost:8085/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<seu_refresh_token>"}'
```

### ❌ CORS error no frontend

**Solução:** Verifique `CORS_ORIGINS` em `config.py`:
```python
CORS_ORIGINS = [
    "http://localhost:8086",  # Next.js dev
    "https://seu-dominio.com",  # Produção
]
```

### ❌ "contato de 'NoneType' não é iterável"

**Solução:** Verifique se há pelo menos 1 usuário no banco:
```bash
python -m app.core.init_db  # Cria dados de seed
```

---

## 📦 Estrutura de Dependências

| Pacote | Versão | Propósito |
|--------|--------|-----------|
| `fastapi` | ^0.104 | Framework web assíncrono |
| `sqlalchemy` | ^2.0 | ORM assíncrono |
| `asyncpg` | ^0.28 | Driver PostgreSQL async |
| `pydantic` | ^2.0 | Validação de dados |
| `python-multipart` | ^0.0.6 | Upload de formulários |
| `bcrypt` | ^4.1 | Hash de senhas |
| `python-jose[cryptography]` | ^3.3 | JWT HS256 |
| `alembic` | ^1.13 | Migrações de BD |
| `pytest` | ^7.4 | Framework de testes |
| `pytest-asyncio` | ^0.21 | Suporte a async em pytest |
| `httpx` | ^0.25 | Cliente HTTP para testes |

---

## 🎯 Otimizações em Produção

- ✅ **Connection Pooling:** SQLAlchemy automático (`pool_pre_ping=True`)
- ✅ **Compression:** Gzip automático via middleware FastAPI
- ✅ **Caching Headers:** `Cache-Control` no GET /api/contatos
- ✅ **Rate Limiting:** Implementar via `slowapi` se necessário
- ✅ **Logging:** Estruturado em JSON para ELK/DataDog
- ✅ **Health Check:** GET `/health` para load balancers

---
