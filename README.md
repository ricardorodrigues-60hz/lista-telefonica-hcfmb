# 📞 Aciono Você — Lista Telefônica Hospitalar

![Status](https://img.shields.io/badge/status-Em%20desenvolvimento-orange)
![Versão](https://img.shields.io/badge/vers%C3%A3o-1.0.0-blue)
![Licença](https://img.shields.io/badge/licen%C3%A7a-MIT-green)

O **Aciono Você** é um sistema de contatos e ramais institucionais construído para o HCFMB (UNESP). Ele funciona como um aplicativo web progressivo (PWA) offline-first.

Ele é extremamente útil para hospitais e instituições onde a conectividade pode ser intermitente. Os usuários podem consultar a lista telefônica e até mesmo realizar alterações enquanto estão desconectados da internet. Assim que a conexão é restabelecida, o sistema sincroniza os dados automaticamente com o servidor.

## Funcionalidades e Demonstração

- **Offline-First:** Consulte e gerencie contatos mesmo sem internet.
- **Sincronização Automática:** Atualizações feitas offline são enviadas ao backend assim que a rede volta, com resolução de conflitos (last-write-wins).
- **Controle de Acesso (RBAC):** Papéis definidos para Gestores (podem criar, editar e excluir contatos) e Consultores (apenas leitura e sincronização).
- **Instalável:** Pode ser instalado em celulares e computadores como um aplicativo nativo (PWA).
- **Trilha de Auditoria:** Histórico detalhado de todas as alterações feitas no banco de dados.

> *(Espaço reservado para capturas de tela ou um arquivo .gif demonstrando a aplicação em funcionamento)*

## Tecnologias

O projeto é dividido em duas aplicações principais (backend e frontend):

- **Backend:** Python 3.11, FastAPI, SQLAlchemy 2 (async), Pydantic, Alembic
- **Frontend:** Node.js, Next.js 16 (App Router), React 19, Dexie.js, TypeScript 5
- **Banco de Dados Local (Navegador):** IndexedDB
- **Banco de Dados Servidor:** SQLite (para desenvolvimento) / PostgreSQL (para produção)
- **Infraestrutura:** Docker e Docker Compose

## Como Instalar e Executar

A maneira mais rápida de rodar toda a aplicação localmente é usando o Docker.

### Pré-requisitos
- Ter o **Git** instalado.
- Ter o **Docker** e o **Docker Compose** instalados na sua máquina.

### Passo 1: Clonar o repositório
```bash
git clone https://github.com/seu-usuario/lista_telefonica_acionovoce.git
cd lista_telefonica_acionovoce
```

### Passo 2: Instalar as dependências
*(No uso com Docker, as dependências são instaladas automaticamente dentro dos contêineres na etapa de build.)*

### Passo 3: Iniciar a aplicação
```bash
docker compose up -d --build
```
Isso vai criar e iniciar os contêineres do backend (na porta `8085`) e do frontend (na porta `8086`). O banco de dados SQLite será criado e preenchido com dados de demonstração (seeds).

### Passo 4: Acessar a aplicação
- **Frontend:** Acesse `http://localhost:8086` no seu navegador.
- **Backend (Documentação da API):** Acesse `http://localhost:8085/docs`.

Para rodar os serviços individualmente de forma manual (sem Docker), consulte os manuais específicos:
- [Instruções do Backend](backend/README.md)
- [Instruções do Frontend](frontend/README.md)
