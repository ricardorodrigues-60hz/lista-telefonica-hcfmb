# Frontend — Aciono Você (Next.js)

Interface PWA da lista telefônica hospitalar. Funciona offline via IndexedDB (Dexie.js) e sincroniza com o backend quando a conexão retorna.

**Stack:** Next.js 16 · React 19 · TypeScript · Dexie.js

---

## Instalação

**Requisitos:** Node.js 20+ · npm 10+

```bash
# Na pasta frontend/
npm install
npm run dev       # http://localhost:8086
```

Crie o arquivo `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8085
NEXT_PUBLIC_DEBUG=true
```

---

## Scripts

| Script             | Descrição                          |
|--------------------|------------------------------------|
| `npm run dev`      | Desenvolvimento com hot-reload     |
| `npm run build`    | Build de produção                  |
| `npm run start`    | Serve o build de produção          |
| `npm run lint`     | ESLint                             |
| `npm run type-check` | Verificação de tipos TypeScript  |

---

## Estrutura de pastas

```
frontend/
├── public/             # Manifest, service worker, ícones
├── src/
│   ├── app/            # Rota principal (page.tsx, layout.tsx, globals.css)
│   └── db/             # Schema Dexie (IndexedDB)
├── next.config.ts
├── tsconfig.json
└── package.json
```

---

## Sincronização offline

O app opera normalmente sem conexão. Operações de CRUD são gravadas localmente via Dexie. Ao detectar o evento `online`, o app envia os dados pendentes para `POST /contatos/sync` e atualiza o banco local com a resposta do servidor.

Conflitos são resolvidos por **last-write-wins**: o `atualizado_em` mais recente prevalece.

---

## Docker

```bash
# Apenas o frontend
docker compose up -d --build frontend

# Tudo junto
docker compose up -d --build
```

---

## Troubleshooting

| Erro | Solução |
|------|---------|
| `EACCES: permission denied` | `npm cache clean --force` e reinstale |
| `Cannot find module '@/db'` | Verifique o alias `@/*` em `tsconfig.json` |
| `NEXT_PUBLIC_API_URL not defined` | Crie ou corrija `.env.local` |
| Service Worker não ativa | DevTools → Application → Service Workers |
