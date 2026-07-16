# Aciono Você – Lista Telefônica Hospitalar

Sistema de lista telefônica institucional desenvolvido para o HCFMB (Hospital das Clínicas da Faculdade de Medicina de Botucatu). Funciona como PWA offline-first: os dados ficam disponíveis localmente e sincronizam com o servidor quando a conexão retorna.

**Stack:** FastAPI (Python) · Next.js + React · SQLite / PostgreSQL · Docker

---

## Estrutura do repositório

```
lista_telefonica_acionovoce/
├── backend/    # API REST (FastAPI)
├── frontend/   # Interface web (Next.js / PWA)
└── docker-compose.yml
```

Cada subprojeto tem seu próprio README com instruções de instalação e variáveis de ambiente.

---

## Subir tudo com Docker

```bash
docker compose up -d --build
```

| Serviço   | Porta |
|-----------|-------|
| Backend   | 8085  |
| Frontend  | 8086  |

A aplicação fica acessível em `http://localhost:8086`.

---

## Desenvolvimento local

Prefere rodar sem Docker? Veja os READMEs internos:

- [`backend/README.md`](./backend/README.md) — API FastAPI
- [`frontend/README.md`](./frontend/README.md) — App Next.js

---

## Papéis de usuário

| Papel      | Permissões                        |
|------------|-----------------------------------|
| GESTOR     | Criar, editar e excluir contatos  |
| CONSULTOR  | Apenas visualizar                 |

A autenticação é feita via header `x-user-id`. Sem JWT externo por enquanto — o sistema mapeia o ID para um papel fixo.

---