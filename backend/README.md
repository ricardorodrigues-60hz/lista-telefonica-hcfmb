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
- **Banco de dados:** SQLite (`aiosqlite`) para dev, escalável para PostgreSQL (`asyncpg`)
- **Migrações:** Alembic
- **Validação de Dados:** Pydantic 2.13
- **Testes:** pytest, pytest-asyncio, httpx

## Como Instalar e Executar

Se preferir rodar o backend localmente sem o Docker Compose da raiz, siga os passos abaixo:

### Pré-requisitos
- Python 3.11 ou superior instalado.
- Ambiente virtual (venv).

### Passo 1: Clonar o repositório
```bash
git clone https://github.com/seu-usuario/lista_telefonica_acionovoce.git
cd lista_telefonica_acionovoce/backend
```

### Passo 2: Instalar as dependências
Crie um ambiente virtual, ative-o e instale os pacotes necessários:
```bash
# Criar o ambiente virtual
python -m venv .venv

# Ativar no Windows:
.\.venv\Scripts\activate
# Ativar no Linux/macOS:
# source .venv/bin/activate

# Instalar pacotes
pip install -r requirements.txt
```

### Passo 3: Inicializar banco de dados e migrações
```bash
alembic upgrade head
```

### Passo 4: Iniciar a aplicação
Você pode rodar a aplicação habilitando a criação de dados de demonstração (seeds) na inicialização:
```bash
# No Windows PowerShell:
$env:RUN_SEEDS="1"; uvicorn app.main:app --reload --port 8085

# No Linux/Mac/Git Bash:
RUN_SEEDS=1 uvicorn app.main:app --reload --port 8085
```
A API estará disponível em `http://localhost:8085`. A documentação interativa pode ser vista em `http://localhost:8085/docs`.
