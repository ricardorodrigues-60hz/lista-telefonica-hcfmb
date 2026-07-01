# 📞 Aciono Você — Backend (FastAPI)

[![CI](https://img.shields.io/badge/CI-pending-lightgrey)]

## Sumário
- [Visão geral](#visão-geral)
- [Arquitetura](#arquitetura)
- [Instalação](#instalação)
- [Execução](#execução)
- [Migrações](#migrações)
- [Seed de Dados](#seed-de-dados)
- [Endpoints da API](#endpoints-da-api)
- [Schema de Dados](#schema-de-dados)
- [Testes Automatizados](#testes-automatizados)
- [Troubleshooting](#troubleshooting)
- [CI](#ci)

## Visão geral
Esta API **FastAPI** fornece endpoints para gerenciamento de usuários e contatos hospitalares, suportando sincronização offline‑first, autenticação JWT e controle de acesso granular (RBAC).

## Arquitetura
```mermaid
flowchart TD
    subgraph FastAPI[FastAPI Application]
        A[app/main.py] --> B[routers]
        B --> C[schemas]
        B --> D[core (auth, config)]
        B --> E[repositories]
        E --> F[SQLAlchemy (Async) + PostgreSQL]
    end
```

## Instalação
| Pré‑requisito | Versão |
|---|---|
| Python | 3.11+ |
| PostgreSQL | 14+ |
| virtualenv | any |

```bash
# Crie e ative o ambiente virtual (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
# Instale dependências
pip install -r requirements.txt
```

Crie o arquivo `.env` na raiz de **backend/** com as variáveis abaixo (exemplo):
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/lista_telefonica
SECRET_KEY=sua_chave_secreta_muito_longa_aqui_minimo_32_caracteres
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
API_PORT=8085
```

## Execução
```bash
# Desenvolvimento (auto‑reload)
uvicorn app.main:app --reload --port ${{ env.API_PORT }}

# Produção (workers)
uvicorn app.main:app --workers 4 --port ${{ env.API_PORT }}
```

### Docker Compose
```bash
docker compose up -d --build backend
```

## Migrações
```bash
# Gerar nova migração
alembic revision --autogenerate -m "descrição da mudança"
# Aplicar migrações pendentes
alembic upgrade head
```

## Seed de Dados
```bash
python -m app.core.init_db
```
Esse comando cria usuários de teste (`RI98234` gestor, `RI98235` consultor) e alguns contatos de exemplo.

## Endpoints da API
| Verbo | Rota | Descrição | Exemplo `curl` |
|---|---|---|---|
| POST | `/api/auth/login` | Autenticação e obtenção de tokens | `curl -X POST http://localhost:8085/api/auth/login -H "Content-Type: application/json" -d '{"usuario_id_externo":"RI98234","senha":"senha123"}'` |
| POST | `/api/auth/refresh` | Renovar access token | `curl -X POST http://localhost:8085/api/auth/refresh -H "Content-Type: application/json" -d '{"refresh_token":"<token>"}'` |
| GET | `/api/contatos/` | Listar contatos (paginado) | `curl -H "Authorization: Bearer <token>" "http://localhost:8085/api/contatos/?skip=0&limit=10"` |
| POST | `/api/contatos/criar-editar` | Criar ou atualizar contato (gestor) | `curl -X POST http://localhost:8085/api/contatos/criar-editar -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{...}'` |
| DELETE | `/api/contatos/deletar/{id}` | Soft‑delete de contato (gestor) | `curl -X DELETE http://localhost:8085/api/contatos/deletar/<id> -H "Authorization: Bearer <token>"` |
| POST | `/api/contatos/sync` | Sincronização offline‑first | `curl -X POST http://localhost:8085/api/contatos/sync -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"contatos":[...]}'` |

## Schema de Dados
```python
class TipoNumero(str, Enum):
    institucional = "institucional"
    publico = "publico"

class Papel(str, Enum):
    consultor = "consultor"
    gestor = "gestor"
```

## Testes Automatizados
```bash
cd backend
pytest -v               # Executa todos os testes
pytest --cov=app --cov-report=html   # Gera relatório de cobertura
```
Os testes utilizam **pytest‑asyncio** e um banco SQLite em memória.

## Troubleshooting
- **ModuleNotFoundError: 'app'** – Certifique‑se de estar na pasta `backend/` ao rodar os módulos com `python -m`.
- **Database not found** – Crie o banco PostgreSQL (`createdb lista_telefonica`) ou ajuste `DATABASE_URL` para SQLite.
- **Token expirado (401)** – Use o endpoint `/api/auth/refresh` para renovar.
- **CORS errors** – Verifique as origens permitidas em `core/config.py`.

## CI
A pipeline CI está configurada (ex.: GitHub Actions) porém desatualizada. Atualizações podem ser feitas posteriormente.
