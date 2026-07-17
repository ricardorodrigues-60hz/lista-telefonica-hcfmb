# 📞 Aciono Você — Frontend (Next.js 16 + React 19)

PWA offline-first: persiste contatos localmente via **Dexie.js** (IndexedDB) e sincroniza com o backend quando há conexão. Visão geral do produto: [`../README.md`](../README.md).

## Desenvolvimento

```bash
npm install
npm run dev   # http://localhost:8086
```

Requer o backend em `http://localhost:8085` (ou `NEXT_PUBLIC_API_URL` apontando para outro host).

| Script | Uso |
|---|---|
| `npm run dev` | servidor de desenvolvimento (porta 8086) |
| `npm run build` | build de produção |
| `npm run start` | serve a build de produção |
| `npm run lint` | ESLint |

## Estrutura

```
src/
├── app/
│   ├── page.tsx      # login, CRUD, sincronização, status de conexão (componente único)
│   ├── layout.tsx
│   └── globals.css   # tema/paleta HCFMB
└── db/
    └── db.ts          # schema Dexie.js (LocalContato, AcionoVoceDB)
public/                # manifest.json, sw.js (Service Worker via @ducanh2912/next-pwa)
```

## Sincronização Offline

1. Toda escrita local grava em Dexie com `sincronizado: false`.
2. O evento `window.online` dispara a sincronização automaticamente.
3. Registros pendentes (`sincronizado === false`) são enviados em lote para `POST /api/sync`.
4. O backend resolve conflitos por `atualizado_em` (last-write-wins) e retorna `contatos_atualizados` (UUIDs confirmados).
5. O frontend marca esses UUIDs como `sincronizado: true`; a UI é reativa via `useLiveQuery`.

## Schema Local (`src/db/db.ts`)

```typescript
export interface LocalContato {
  id: string;                            // UUID v4
  nome: string;
  telefone: string;
  email?: string;
  tipo_numero: 'institucional' | 'publico';
  atualizado_em: string;                 // ISO 8601 UTC — árbitro de conflito
  sincronizado: boolean;                 // só existe localmente, nunca enviado ao servidor
  excluido: boolean;                     // soft delete
}
```

Alterações no schema exigem uma nova `db.version(n)` no Dexie.

## Variáveis de Ambiente

| Variável | Descrição |
|---|---|
| `NEXT_PUBLIC_API_URL` | URL base da API (ex.: `http://localhost:8085`) |

Variáveis com prefixo `NEXT_PUBLIC_` são embutidas no bundle e expostas ao navegador.

## PWA

Manifest em `public/manifest.json` e Service Worker (`public/sw.js`, gerado via `@ducanh2912/next-pwa`) cacheiam os assets estáticos e permitem instalação como app. Chamadas à API não ficam cacheadas indefinidamente — checar o registro do Service Worker em DevTools → Application se o modo offline não funcionar.

## Docker

```bash
docker compose up -d --build frontend   # a partir da raiz do projeto
```

`Dockerfile` faz `npm install` + `npm run build` e serve com `npm run start` na porta 8086.

## Troubleshooting

- **`NEXT_PUBLIC_API_URL` não aplicada** — variáveis `NEXT_PUBLIC_*` são resolvidas em build time; reconstrua após alterá-las.
- **Dexie.js retorna vazio na primeira renderização** — normal com `useLiveQuery`; aguarde a primeira emissão antes de assumir "sem dados".
- **Service Worker não atualiza** — limpe em DevTools → Application → Clear site data.

## Dependências Principais

| Pacote | Uso |
|---|---|
| `next` / `react` / `react-dom` | framework e UI (Next 16, React 19) |
| `dexie` / `dexie-react-hooks` | IndexedDB + `useLiveQuery` |
| `lucide-react` | ícones |
| `@ducanh2912/next-pwa` | manifest + Service Worker |
