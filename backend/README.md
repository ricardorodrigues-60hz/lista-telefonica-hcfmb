# Backend — Lista Telefônica (ação: novo)

> README específico para a pasta `backend` com instruções práticas de setup, execução, testes e CI.

---

## Visão geral

Este serviço fornece endpoints REST para gerenciamento de usuários e contatos.
Principais tecnologias:
- FastAPI
- Pydantic v2
- SQLAlchemy (async)
- pytest + pytest-asyncio


## Pré-requisitos

- Python 3.11 (testado)
- Git
- Opcional: Docker se preferir executar via container


## Setup local (rápido)

1. Criar e ativar ambiente virtual (exemplo cross-platform):

Windows PowerShell

```powershell
python -m venv .venv
& .venv\Scripts\Activate.ps1
```

Windows (cmd)

```cmd
python -m venv .venv
.\.venv\Scripts\activate
```

Unix / macOS

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Instalar dependências:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

3. Executar testes (usa `PYTHONPATH=.` ou `PYTHONPATH=backend` dependendo do seu shell):

```bash
# estando na raiz do repo
cd backend
python -m pytest -q
```


## Executando a API em modo desenvolvimento

Ative o venv conforme acima e então:

```bash
# estando dentro de backend/ ou com PYTHONPATH apontando
uvicorn app.main:app --reload --port 8000
```

Endpoints principais ficam sob `/api` conforme configuração em `app/main.py`.


## Variáveis de ambiente importantes

- `DATABASE_URL`: URL SQLAlchemy. Se não definido, o projeto usa SQLite em memória (`sqlite+aiosqlite:///:memory:`) para facilitar testes locais.
- `RUN_SEEDS`: se `1`, executa as seeds no startup (`app.core.init_db.seeds()`).
- `SECRET_KEY`: chave para JWT. Se não definida, verifique `app/core/config.py` para o valor padrão (aconselhado configurar em produção).
- `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`, `ALGORITHM`: parâmetros de JWT.

Exemplo para usar Postgres (apenas quando o Postgres estiver pronto):

```bash
export DATABASE_URL='postgresql+asyncpg://user:pass@host:5432/dbname'
export RUN_SEEDS=1
```

Observação: para Postgres é necessário instalar `asyncpg` no ambiente.


## Banco de dados

- Com `DATABASE_URL` vazio, o código seleciona automaticamente SQLite (`aiosqlite`) para testes locais.
- Para mudar para Postgres, sete `DATABASE_URL` e instale `asyncpg`.


## Testes e dicas

- Executar apenas a suíte de backend:

```bash
cd backend
python -m pytest -q
```

- Se encontrar erro do tipo `ModuleNotFoundError: asyncpg` e você pretende usar Postgres, instale `asyncpg`:

```bash
python -m pip install asyncpg
```

- Para testes que fazem chamadas HTTP internas usamos `httpx.AsyncClient(transport=ASGITransport(app=app))` — não é necessário rodar o servidor.


## Arquivos úteis

- `app/main.py` — inicialização da aplicação. Veja [app/main.py](app/main.py#L1).
- `app/core/config.py` — leitura de configurações/variáveis de ambiente. Veja [app/core/config.py](app/core/config.py#L1).
- `app/database.py` — criação do engine assíncrono e `get_db()` dependency. Veja [app/database.py](app/database.py#L1).
- `app/core/init_db.py` — rotina de migração/seed segura; controlada por `RUN_SEEDS`. Veja [app/core/init_db.py](app/core/init_db.py#L1).
- `app/core/passwords.py` — helpers async para hashing/verificação de senha. Veja [app/core/passwords.py](app/core/passwords.py#L1).
- `backend/tests/` — suíte de testes. Exemplos: [tests/test_usuarios_endpoints.py](tests/test_usuarios_endpoints.py#L1), [tests/test_auth_endpoints.py](tests/test_auth_endpoints.py#L1).


## CI

Incluí um workflow GitHub Actions em `.github/workflows/ci.yml` que executa os testes em pushes e PRs para `main`, `master` e `beta-0`.
Arquivo: [.github/workflows/ci.yml](.github/workflows/ci.yml#L1)


## Executando com Docker (opcional)

O projeto contém `backend/Dockerfile`. Exemplo rápido de build/run (ajuste variáveis de ambiente):

```bash
docker build -t lista-telefonica-backend -f backend/Dockerfile .
docker run -e DATABASE_URL='sqlite+aiosqlite:///:memory:' -p 8000:8000 lista-telefonica-backend
```


## Troubleshooting rápido

- `Pydantic from_orm deprecation`: já convertemos chamadas para `model_validate` e configuramos `model_config` onde apropriado.
- `missing asyncpg` → instale `asyncpg` se usar Postgres.
- `aiosqlite` faltando → `python -m pip install aiosqlite`.


## Próximos passos recomendados

- Adicionar workflow de CI para linting/static analysis (flake8, mypy).
- Adicionar instruções de migração (ex.: Alembic) se migrar para Postgres em produção.


