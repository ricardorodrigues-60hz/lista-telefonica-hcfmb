# Backend — Aciono Você (FastAPI)

API REST assíncrona para gerenciamento de contatos hospitalares, com suporte a sincronização offline-first, controle de acesso por papel (GESTOR / CONSULTOR) e montagem flexível via prefixo configurável (`API_BASE`).

**Stack:** Python 3.11 · FastAPI · SQLAlchemy (async) · SQLite (dev) / PostgreSQL (prod)

---

## Instalação

```bash
# Na pasta backend/
python -m venv .venv
.\.venv\Scripts\Activate.ps1      # Windows
# source .venv/bin/activate       # Linux/Mac

pip install -r requirements.txt
```

Crie o arquivo `.env` (copie de `.env.example` se existir):

```env
DATABASE_URL=sqlite+aiosqlite:///./lista.db
SECRET_KEY=troque-em-producao
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
API_PORT=8085
API_BASE=/lista-telefonica
```

> Em produção, gere `SECRET_KEY` com:
> `python -c "import secrets; print(secrets.token_urlsafe(32))"`

---

## Executar

```bash
# Desenvolvimento (com reload automático)
uvicorn app.main:app --reload --port 8085

# Docs interativos
# http://localhost:8085/docs
```

---

## Scripts utilitários

```bash
# Inicializar banco (cria as tabelas)
.venv\Scripts\python -m scripts.init_db

# Popular com dados mock para desenvolvimento
.venv\Scripts\python -m scripts.seed_mock

# Recriar banco do zero e re-popular
.venv\Scripts\python -m scripts.seed_mock --reset
```

---

## Estrutura de pastas

```
backend/
├── app/
│   ├── main.py               # Inicialização e lifecycle do FastAPI
│   ├── core/
│   │   ├── config.py         # Configuração via pydantic-settings (.env)
│   │   ├── database.py       # Engine e sessão assíncrona (SQLAlchemy)
│   │   ├── auth.py           # Dependências de autenticação (Depends)
│   │   ├── init_db.py        # Inicialização do banco (create_all)
│   │   └── auth/service.py   # Lógica de JWT
│   └── modules/contatos/
│       ├── models.py         # Modelo ORM (tabela contatos)
│       ├── schemas.py        # Schemas Pydantic (request/response)
│       ├── repository.py     # Queries e lógica de sync
│       └── router.py         # Endpoints HTTP
├── scripts/
│   ├── init_db.py            # Script standalone de inicialização
│   └── seed_mock.py          # Dados de exemplo para desenvolvimento
├── tests/
│   ├── test_contatos_endpoints.py
│   └── test_schemas.py
├── requirements.txt
└── Dockerfile
```

---

## Endpoints principais

| Método | Rota                        | Papel mínimo | Descrição                    |
|--------|-----------------------------|--------------|------------------------------|
| GET    | `/contatos/`                | CONSULTOR    | Lista contatos ativos        |
| POST   | `/contatos/`                | GESTOR       | Cria novo contato            |
| PUT    | `/contatos/{id}`            | GESTOR       | Atualiza contato existente   |
| DELETE | `/contatos/{id}`            | GESTOR       | Soft-delete (marca excluído) |
| POST   | `/contatos/sync`            | CONSULTOR    | Sincronização offline-first  |

A autenticação é feita via header `x-user-id`. O sistema mapeia o ID para um papel (GESTOR ou CONSULTOR).

---

## Sincronização offline

Quando o cliente reconecta, envia um lote de contatos via `POST /contatos/sync`. O backend aplica a estratégia **last-write-wins**: o `atualizado_em` mais recente prevalece. Registros marcados como deletados recebem soft-delete no servidor.

---

## Testes

```bash
# Todos os testes
.venv\Scripts\pytest -q

# Com cobertura
.venv\Scripts\pytest --cov=app --cov-report=html
```

Os testes usam SQLite em memória — nenhuma dependência externa necessária.

> Para rodar em CI, defina `API_BASE=/api` nas variáveis de ambiente da pipeline.
