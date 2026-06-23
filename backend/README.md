# Aciono Você - Lista Telefônica Hospitalar (Backend)

Este módulo constitui o backend do sistema **Aciono Você**, um submódulo de lista telefônica hospitalar de alta criticidade e disponibilidade. Projetado especificamente para operar sob o padrão **Offline-First**, o backend fornece endpoints de alta performance para sincronização bidirecional de contatos, controle de acesso e auditoria completa de alterações.

O sistema foi estruturado para ser montado de forma modular (como um sub-app FastAPI via `.mount`) dentro de um portal hospitalar corporativo unificado.

---

## 🏛️ Arquitetura do Sistema

A aplicação adota boas práticas de Clean Architecture e design patterns consagrados no ecossistema Python:

```mermaid
graph TD
    Client[Cliente SPA/PWA] --> Routers[Routers/Endpoints FastAPI]
    Routers --> Dependencies[Injeção de Dependências - Depends]
    Dependencies --> Repositories[Padrão Repository]
    Repositories --> SQLAlchemy[SQLAlchemy Async Engine]
    SQLAlchemy --> DB[(Banco de Dados PostgreSQL)]
```

### 1. Padrão Repository
Toda a lógica de acesso a dados está encapsulada em classes Repository (como `ContatoRepository`). Isso isola a camada de apresentação/rotas das regras específicas de persistência do ORM, facilitando a testabilidade através de dublês de teste (mocks) e garantindo baixo acoplamento.

### 2. SQLAlchemy Assíncrono (async/await)
Todas as operações de I/O de banco de dados utilizam a API assíncrona do SQLAlchemy 2.0 com `asyncpg`. Isso maximiza o throughput da API sob alta concorrência de requisições simultâneas.

### 3. Integração Offline-First
O backend implementa uma estratégia de **sincronização baseada em timestamp**. 
- O cliente envia modificações locais (realizadas offline no IndexedDB) com seus respectivos timestamps de atualização (`atualizado_em`).
- O servidor compara as datas e resolve conflitos usando a política *last-write-wins* baseada em fuso horário (UTC), aplicando as mudanças e retornando apenas os registros criados ou alterados por outros usuários desde a última sincronização do cliente.

---

## 🔐 Controle de Acesso e Auditoria

### Tabela de Vínculo de Permissões
A aplicação possui um modelo enxuto de usuário integrado a sistemas corporativos de SSO (Single Sign-On):
* **Identificação:** O usuário é referenciado unicamente pelo seu `usuario_id_externo` corporativo (ex: `RI98234`).
* **Papéis (RBAC):** Suporta os perfis `gestor` (com privilégios de escrita, edição e exclusão) e `consultor` (apenas leitura e sincronização de dados).

### Trilha de Auditoria (Audit Trail)
Qualquer operação de escrita (criação, edição ou exclusão lógica) gera um registro de auditoria imutável na tabela `audit_trails`. 
* Registra o tipo da ação (`criar`, `atualizar`, `deletar`).
* Armazena o ID externo do operador (`usuario_id_externo`) que realizou a ação.
* Salva o estado dos dados modificados em formato JSON.

---

## ⚙️ Configuração e Montagem como Sub-app

Para viabilizar a integração transparente no ecossistema do hospital, o app expõe o parâmetro `TOKEN_URL` no `config.py` e parametriza o `OAuth2PasswordBearer` dinamicamente. Desta forma, ele pode ser montado dentro de outro app FastAPI:

```python
from fastapi import FastAPI
from app.main import app as lista_telefonica_app

parent_app = FastAPI()

# Montando o módulo de lista telefônica
parent_app.mount("/lista-telefonica", lista_telefonica_app)
```

---

## 🚀 Instalação e Execução

### Pré-requisitos
* Python 3.11+
* Docker e Docker Compose (opcional)

### Execução Local com Virtualenv

1. Instale as dependências:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Ou .\.venv\Scripts\activate no Windows
   pip install -r requirements.txt
   ```

2. Configure o arquivo `.env`:
   ```env
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/lista_telefonica
   SECRET_KEY=sua_chave_secreta_aqui
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   ```

3. Execute as migrações do banco de dados (Alembic):
   ```bash
   alembic upgrade head
   ```

4. Alimente o banco com os dados iniciais (Seeds):
   ```bash
   python -m app.core.init_db
   ```

5. Inicie o servidor:
   ```bash
   uvicorn app.main:app --port 8085
   ```

### Execução Completa via Docker

Toda a infraestrutura (frontend, backend e banco de dados PostgreSQL) pode ser inicializada via Docker Compose a partir da raiz do projeto:

```bash
docker compose up -d --build
```

O backend estará acessível em `http://localhost:8085` e a documentação interativa em `http://localhost:8085/docs`.

---

## 🧪 Testes Automatizados

A suíte de testes do backend utiliza `pytest` e `pytest-asyncio` com banco de dados em memória para garantir consistência.

Para rodar todos os testes localmente:
```bash
pytest -q
```
