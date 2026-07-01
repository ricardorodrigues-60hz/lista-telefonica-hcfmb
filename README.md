# 📞 Aciono Você – Lista Telefônica Hospitalar (HCFMB)

[![CI](https://img.shields.io/badge/CI-pending-lightgrey)]

## Sumário
- [Visão geral](#visão-geral)
- [Arquitetura da solução](#arquitetura-da-solução)
- [Execução completa (Docker Compose)](#execução-completa-docker-compose)
- [Roadmap](#roadmap)
- [Changelog](#changelog)

## Visão geral
Aplicação **offline‑first** composta por um **backend FastAPI** (Python) e um **frontend PWA** (Next.js 16 + React 19). O backend gerencia usuários, contatos e sincronização bidirecional; o frontend oferece UI responsiva com persistência local via IndexedDB (Dexie.js) e sincroniza alterações quando a conexão retorna.

## Arquitetura da solução
```mermaid
flowchart LR
    subgraph Frontend[Frontend (Next.js)]
        FE[UI React] --> DB[Dexie.js (IndexedDB)]
        FE --> SW[Service Worker]
    end
    subgraph Backend[Backend (FastAPI)]
        BE[FastAPI App] --> DBPost[PostgreSQL]
    end
    FE -- API calls --> BE
    DB -- Sync payload --> BE
    SW -- Cache assets & API --> BrowserCache[(Browser Cache)]
```

## Execução completa (Docker Compose)
```bash
# Na raiz do repositório
docker compose up -d --build
```
Isso iniciará os containers **backend** (porta 8085) e **frontend** (porta 8086). A aplicação estará acessível em `http://localhost:8086`.

### Variáveis de ambiente (Docker)
```yaml
services:
  backend:
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/lista_telefonica
      - SECRET_KEY=sua_chave_secreta_muito_longa_aqui_minimo_32_caracteres
      - ALGORITHM=HS256
      - ACCESS_TOKEN_EXPIRE_MINUTES=30
      - REFRESH_TOKEN_EXPIRE_DAYS=7
  frontend:
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8085/api
      - NEXT_PUBLIC_DEBUG=true
```

## Roadmap
- **v1.0** – MVP funcional com sincronização offline.
- **v1.1** – Implementar rate‑limiting e logging estruturado.
- **v1.2** – Suporte a múltiplas unidades hospitalares.

## Changelog
| Versão | Data | Alterações |
|---|---|---|
| 1.0.0 | 2026‑06‑30 | Lançamento inicial – backend FastAPI, frontend Next.js, Docker compose.
| 1.0.1 | 2026‑07‑01 | Atualização dos READMEs (documentação técnica).

## CI
A pipeline CI está configurada (ex.: GitHub Actions) mas está desatualizada. Atualizações podem ser feitas posteriormente.