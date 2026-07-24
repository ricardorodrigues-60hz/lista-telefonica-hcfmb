# 📞 Aciono Você — Backend API

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)

Este é o backend do sistema da Lista Telefônica Hospitalar. Ele expõe uma API RESTful assíncrona desenvolvida em FastAPI.

O software é responsável por gerenciar a persistência segura dos dados, controle de acesso através de Tokens JWT, e hospedar o algoritmo de sincronização que recebe lotes de atualizações dos clientes PWA, aplicando as mudanças de acordo com a regra de resolução de conflitos de data (last-write-wins). Ele também mantém uma trilha de auditoria completa de qualquer alteração no banco.

## Funcionalidades e Demonstração

- **Autenticação Segura:** Autenticação baseada em JWT com acesso (curto) e refresh token rotativo.
- **Sincronização Lote:** Rota dedicada `/api/sync` para receber e conciliar dados criados no modo offline pelos clientes móveis.
- **Arquitetura Modular:** Código dividido por domínio (`auth`, `usuarios`, `contatos`, `sync`, `auditoria`).
- **Trilha de Auditoria (AuditTrail):** Todo insert/update/delete registra de forma imutável quem alterou e quais foram os dados modificados.
- **Soft Delete:** Registros apagados não são removidos do banco físico para permitir a propagação correta da exclusão aos clientes offline.

## Tecnologias

- **Linguagem:** Python 3.11+
- **Framework Web:** FastAPI 0.138
- **ORM:** SQLAlchemy 2.0 (assíncrono)
- **Banco de dados:** PostgreSQL (`asyncpg`) executado via Docker Container
- **Migrações:** Alembic
- **Validação de Dados:** Pydantic 2.13
- **Testes:** pytest, pytest-asyncio, httpx

## Como Instalar e Executar

O PostgreSQL é o único banco de dados suportado pelo projeto. Siga os passos para executar via Docker Compose:

### Pré-requisitos
- Docker e Docker Compose instalados.

### Executar via Docker Compose

```bash
docker-compose up -d --build
```

Isso iniciará o container do **PostgreSQL 16** e o serviço da API backend na porta `8085`.

### Execução Local para Desenvolvimento (Com PostgreSQL em Docker)

1. Suba o container do PostgreSQL:
```bash
docker-compose up -d db
```

2. Instale as dependências Python:
```bash
python -m venv .venv
.\.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

3. Execute as migrações do banco de dados:
```bash
alembic upgrade head
```

4. Inicie a API com hot-reload:
```bash
$env:RUN_SEEDS="1"; uvicorn app.main:app --reload --port 8085
```

A API estará disponível em `http://localhost:8085`. A documentação interativa pode ser vista em `http://localhost:8085/docs`.
