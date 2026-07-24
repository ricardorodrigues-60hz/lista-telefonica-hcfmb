# 📞 Aciono Você — Lista Telefônica Hospitalar

![Status](https://img.shields.io/badge/status-Em%20desenvolvimento-orange)
![Versão](https://img.shields.io/badge/vers%C3%A3o-1.0.0-blue)
![Licença](https://img.shields.io/badge/licen%C3%A7a-MIT-green)

O **Aciono Você** é um sistema de contatos e ramais institucionais construído para o HCFMB (UNESP), operando como um aplicativo web progressivo (PWA) offline-first.

---

## 🛠️ Tecnologias

- **Backend:** Python 3.11, FastAPI, SQLAlchemy (Async), Alembic, Poetry, Pytest, Taskipy
- **Frontend:** Next.js, React, TypeScript, Dexie.js (PWA / IndexedDB)
- **Banco de Dados:** PostgreSQL 16
- **Infraestrutura:** Docker, Docker Compose, GitHub Actions

---

## 🐳 Contêineres Docker

O projeto roda em 3 contêineres gerenciados via Docker Compose:

| Contêiner | Serviço | Porta Host:Container |
| :--- | :--- | :--- |
| `lista-postgres` | Banco de dados PostgreSQL 16 | `5432:5432` |
| `lista-backend-api` | Backend FastAPI | `8085:8085` |
| `lista-frontend-pwa` | Frontend Next.js PWA | `8086:8086` |

---

## 🚀 Como Executar Localmente

### Pré-requisitos
- **Git**
- **Docker** e **Docker Compose**
- **PowerShell** (Windows) ou Shell compatível

### Utilizando os Scripts Automáticos (`/scripts`)

Os scripts de automação estão localizados no diretório `/scripts`:

#### 1. Iniciar a aplicação
```powershell
.\scripts\deploy-docker.ps1
```
*(ou `.\scripts\deploy-docker.bat`)*

Sobe todos os contêineres construindo as imagens necessárias.
- **Frontend:** `http://localhost:8086`
- **Backend (Swagger API):** `http://localhost:8085/docs`

#### 2. Reconstruir do zero (sem cache)
```powershell
.\scripts\rebuild-docker.ps1
```
*(ou `.\scripts\rebuild-docker.bat`)*

Remove contêineres e volumes existentes, reconstruindo as imagens sem cache antes de subir os serviços.

#### 3. Executar Linter e Testes Locais
```powershell
.\scripts\test.ps1
```
*(ou `.\scripts\test.bat`)*

Executa em sequência:
1. `poetry run task lint` (Backend)
2. `poetry run task test` (Backend Pytest + Cobertura)
3. `npm run lint` (Frontend)
4. `npm run build` (Frontend Next.js)

---

## 🔄 Pipeline de CI/CD (GitHub Actions)

A pipeline é definida no arquivo `.github/workflows/ci.yml` e dispara automaticamente em qualquer `push` ou `pull_request`.

### Etapas da Esteira CI:
1. **Checkout** do código.
2. **Configuração de ambiente** (Python 3.11 e Node.js 20).
3. **Cache de dependências** (pip, npm e poetry).
4. **Instalação de dependências** do backend e frontend.
5. **Linting do Backend** (`poetry run task lint`).
6. **Testes Unitários/Integração do Backend** (`poetry run task test`).
7. **Linting do Frontend** (`npm run lint`).
8. **Build de Produção do Frontend** (`npm run build`).
9. **Build das Imagens Docker** (`docker-compose build`).
10. **Subida dos Contêineres** (`docker-compose up -d`).
11. **Aguardar serviços ficarem prontos** (PostgreSQL e Backend API).
12. **Health Check simples** (endpoints da API e Frontend).
13. **Teardown e Limpeza** (`docker-compose down -v`).

Caso qualquer etapa falhe, o merge/build é interrompido imediatamente.
