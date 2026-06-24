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

A aplicação adota **Clean Architecture** com separação clara de responsabilidades:

```
┌────────────────────────────────────────────────────────────────┐
│                    FastAPI Application                         │
│                    (app/main.py)                               │
└────────────────────┬───────────────────────────────────────────┘
                     │
  ┌──────────────────┼──────────────────┐
  │                  │                  │
  v                  v                  v
Routers          Schemas           Core (Auth/Config)
(EntryPoints)    (Pydantic v2)      (JWT, RBAC, Passwords)
  │                  │                  │
  └──────────────────┼──────────────────┘
                     │
                     v
            Repository Pattern
        (ContatoRepository, UsuarioRepository)
                     │
                     v
            SQLAlchemy ORM (Async)
         (Models: Usuario, Contato, AuditTrail)
                     │
                     v
        ┌─────────────────────────────┐
        │   PostgreSQL Database       │
        │  (async via asyncpg)        │
        └─────────────────────────────┘
```

### Benefícios da Arquitetura

1. **Separação de Responsabilidades:** Routers (HTTP) → Repositories (Dados) → Models (ORM)
2. **Testabilidade:** Repositories podem ser mockados; testes usam banco em memória (SQLite)
3. **Escalabilidade:** Operações async/await maximizam concorrência
4. **Auditoria:** Toda escrita passa por `AuditTrail` imutável
5. **Segurança:** RBAC via middlewares `require_gestor` e `require_consultor`

---

## 🔧 Componentes Principais

### 1. **Routers** (`routers/`)
Definem os endpoints HTTP e validam entrada/saída via Pydantic schemas:

- **`auth.py`:** Login, refresh token, validação JWT
- **`contatos.py`:** CRUD sync + endpoint `/sync` para offline-first
- **`usuarios.py`:** Gerenciamento de usuários corporativos

### 2. **Repositories** (`repositories/`)
Encapsulam lógica de acesso a dados:

- **`ContatoRepository`:** Queries complexas (sincronização, soft delete, paginação)
- **`UsuarioRepository`:** Busca por `usuario_id_externo`, validação de credenciais

### 3. **Models** (`models/models.py`)
Definem tabelas SQLAlchemy com relacionamentos:

```python
class Usuario(Base):
    """Usuário corporativo com permissões RBAC"""
    __tablename__ = "usuarios"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    usuario_id_externo: Mapped[str] = mapped_column(unique=True)
    senha_hash: Mapped[str]
    papel: Mapped[Papel] = mapped_column(default=Papel.consultor)
    contatos: Mapped[list["Contato"]] = relationship(back_populates="criado_por")

class Contato(Base):
    """Contato ou ramal hospitalar"""
    __tablename__ = "contatos"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    nome: Mapped[str]
    telefone: Mapped[str]
    email: Mapped[Optional[EmailStr]]
    tipo_numero: Mapped[TipoNumero]
    atualizado_em: Mapped[datetime] = mapped_column(default_factory=utcnow)
    excluido: Mapped[bool] = mapped_column(default=False)
    criado_em: Mapped[datetime] = mapped_column(default_factory=utcnow)
    criado_por_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id"))

class AuditTrail(Base):
    """Trilha imutável de todas as operações de escrita"""
    __tablename__ = "audit_trails"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    usuario_id_externo: Mapped[str]
    acao: Mapped[str]  # 'criar', 'atualizar', 'deletar'
    tabela: Mapped[str]
    registro_id: Mapped[UUID]
    dados: Mapped[dict] = mapped_column(JSON)
    criado_em: Mapped[datetime] = mapped_column(default_factory=utcnow)
```

### 4. **Schemas** (`schemas/`)
Validação com Pydantic v2:

```python
class ContatoCreate(BaseModel):
    """Entrada para criar/atualizar contato"""
    id: UUID = Field(default_factory=uuid4)  # Gerado pelo cliente
    nome: str = Field(..., min_length=3, max_length=255)
    telefone: str = Field(..., pattern=r"^\d{8,}$")  # Min 8 dígitos
    email: Optional[EmailStr] = None
    tipo_numero: TipoNumero
    atualizado_em: datetime  # UTC, recebido do cliente

class SyncPayload(BaseModel):
    """Payload de sincronização bidirecional"""
    contatos: list[dict]  # [{ id, atualizado_em, excluido }, ...]

class SyncResponse(BaseModel):
    """Resposta com delta do servidor"""
    contatos_criados: list[ContatoResponse]
    contatos_atualizados: list[ContatoResponse]
    contatos_deletados: list[UUID]
```

### 5. **Core** (`core/`)
Sistema de autenticação, configuração e utilitários:

- **`auth.py`:** JWT, OAuth2PasswordBearer, middlewares RBAC
- **`config.py`:** Variáveis de ambiente via Pydantic Settings
- **`passwords.py`:** Hash/verify assíncrono (bcrypt com thread pool)
- **`init_db.py`:** Seed de dados de teste

---

## 🔐 Autenticação e Autorização

### Fluxo de Autenticação

```mermaid
graph LR
    A[Cliente] -->|POST /api/auth/login| B[Endpoint Login]
    B -->|Valida usuario_id_externo + senha| C{Credenciais OK?}
    C -->|Sim| D["JWT: Access (30min) + Refresh (7d)"]
    C -->|Não| E[401 Unauthorized]
    D -->|Retorna ao cliente| A
    A -->|Authorization: Bearer &lt;token&gt;| F[Endpoint Protegido]
    F -->|Verifica JWT| G{Token válido?}
    G -->|Sim| H[Executa endpoint]
    G -->|Não| I[401 ou 403]
```

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

| Papel | Leitura | Escrita | Sincronização |
|-------|---------|---------|---------------|
| `consultor` | ✅ | ❌ | ✅ |
| `gestor` | ✅ | ✅ | ✅ |

---

## 📡 Endpoints da API

### Autenticação

#### `POST /api/auth/login`
```bash
curl -X POST http://localhost:8085/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"usuario_id_externo": "RI98234", "senha": "senha123"}'
```

**Response (200):**
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

#### `POST /api/auth/refresh`
Renova o access token usando refresh token:
```bash
curl -X POST http://localhost:8085/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJhbGc..."}'
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

#### `POST /api/contatos/sync` (Sincronização Offline)
Endpoint crítico para a estratégia offline-first:

```bash
curl -X POST http://localhost:8085/api/contatos/sync \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "contatos": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "atualizado_em": "2026-06-24T15:35:00Z",
        "excluido": false
      },
      {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "atualizado_em": "2026-06-24T14:20:00Z",
        "excluido": true
      }
    ]
  }'
```

**Response (200) — Delta do Servidor:**
```json
{
  "contatos_criados": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440002",
      "nome": "Novo Contato (criado por outro usuário)",
      "telefone": "2139",
      "atualizado_em": "2026-06-24T16:00:00Z"
    }
  ],
  "contatos_atualizados": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "nome": "Versão atualizada do servidor",
      "atualizado_em": "2026-06-24T15:45:00Z"
    }
  ],
  "contatos_deletados": ["550e8400-e29b-41d4-a716-446655440001"]
}
```

**Regra de Sincronização:**
- Se `cliente.atualizado_em > servidor.atualizado_em` → Aceita alteração do cliente
- Caso contrário → Envia versão atualizada do servidor de volta
- Sempre retorna criações/alterações de outros usuários desde última sincronização

---

## 📊 Schema de Dados

### Enum `TipoNumero`
```python
class TipoNumero(str, Enum):
    institucional = "institucional"  # Ramal interno
    publico = "publico"              # Número público
```

### Enum `Papel`
```python
class Papel(str, Enum):
    consultor = "consultor"  # Apenas leitura + sync
    gestor = "gestor"        # Leitura + escrita + auditoria
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

| Arquivo | Testes | Cobertura |
|---------|--------|-----------|
| `test_auth_endpoints.py` | Login, refresh token, erros | Autenticação 100% |
| `test_contatos_endpoints.py` | CRUD, paginação, filtros | Contatos 100% |
| `test_blocking_password_ops.py` | Hash assíncrono, BCrypt | Segurança 100% |
| `test_schemas.py` | Validação Pydantic | Schemas 100% |
| `test_usuarios_endpoints.py` | RBAC, permissões | Autorização 100% |

### Exemplo: Teste de Sincronização

```python
@pytest.mark.asyncio
async def test_sync_conflito_timestamp():
    """Verifica last-write-wins baseado em atualizado_em"""
    client = TestClient(app)
    
    # 1. Login como gestor
    response = client.post("/api/auth/login", json={
        "usuario_id_externo": "RI98234",
        "senha": "senha123"
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
