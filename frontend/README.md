# 📞 Aciono Você — Frontend PWA

> Camada de apresentação e persistência offline do sistema de Lista Telefônica Hospitalar do HCFMB · UNESP.

Esta aplicação é um Progressive Web App (PWA) desenvolvido em **Next.js 16** com **React 19**, projetado para funcionar com plena capacidade mesmo sem conexão de rede, utilizando **Dexie.js** para gerenciar o armazenamento local via IndexedDB.

---

## 🚀 Iniciando o Desenvolvimento

### Pré-requisitos

- Node.js 20 ou superior
- npm 10 ou superior

### Instalação e execução

```bash
# Instalar dependências
npm install

# Iniciar o servidor de desenvolvimento (porta 8086)
npm run dev
```

Acesse **http://localhost:8086** no navegador.

---

## 🏗️ Scripts Disponíveis

| Script | Descrição |
|---|---|
| `npm run dev` | Servidor de desenvolvimento com hot-reload |
| `npm run build` | Compilação otimizada para produção |
| `npm run start` | Serve a build de produção |
| `npm run lint` | Verificação de qualidade de código com ESLint |

---

## 📁 Estrutura de Pastas

```
frontend/src/
├── app/
│   ├── page.tsx         # Componente principal: login, lista, CRUD, sync offline
│   ├── layout.tsx       # Layout raiz da aplicação
│   └── globals.css      # Design System: paleta de cores, tipografia, componentes HCFMB
└── db/
    └── db.ts            # Schema do Dexie.js (IndexedDB) — LocalContato, AcionoVoceDB
```

---

## 🔄 Lógica de Sincronização Offline

O frontend implementa um ciclo completo de sincronização offline-first:

1. **Leitura:** `useLiveQuery` do Dexie.js mantém a UI sempre reativa ao IndexedDB local.
2. **Escrita Offline:** Toda criação/edição/exclusão é persistida localmente com `sincronizado: false`.
3. **Retomada Online:** O listener `window.addEventListener('online', ...)` dispara `triggerSync()` automaticamente ao recuperar a conexão.
4. **Sincronização em Lote:** O método `triggerSync()` coleta todos os registros pendentes e envia via `POST /api/contatos/sync`.
5. **Confirmação:** O servidor responde com `contatos_atualizados` (lista de UUIDs). O frontend marca cada um com `sincronizado: true` no Dexie.js ou remove fisicamente os soft-deletados confirmados.

---

## 🗄️ Schema Local (Dexie.js / IndexedDB)

```typescript
export interface LocalContato {
  id: string;             // UUID gerado pelo cliente (crypto.randomUUID())
  nome: string;
  telefone: string;
  email?: string;
  tipo_numero: 'institucional' | 'publico';
  atualizado_em: string;  // ISO 8601 UTC — árbitro de conflitos
  sincronizado: boolean;  // false = alteração pendente de envio ao servidor
  excluido: boolean;      // Soft Delete — propagado na sincronização
}
```

> A chave `sincronizado` é **exclusiva do cliente** e não é enviada ao servidor.

---

## 🌐 Configuração da API

A URL base da API está definida como constante em `src/app/page.tsx`:

```typescript
const API_BASE = 'http://localhost:8085/api';
```

Para produção, altere para a URL do servidor real ou exporte via variável de ambiente `NEXT_PUBLIC_API_URL`.

---

## 🐳 Docker (Produção)

O `Dockerfile` do frontend realiza a compilação estática antes de iniciar o servidor:

```dockerfile
RUN npm run build
CMD ["npm", "run", "start"]
```

Isso garante performance máxima e comportamento estável em ambiente hospitalar.

---

## 📦 Dependências Principais

| Pacote | Versão | Uso |
|---|---|---|
| `next` | 16.2 | Framework React com App Router |
| `react` / `react-dom` | 19 | Biblioteca de UI |
| `dexie` | 4.4 | ORM para IndexedDB (persistência offline) |
| `dexie-react-hooks` | 4.4 | `useLiveQuery` para reatividade ao IndexedDB |
| `lucide-react` | 1.20 | Ícones premium |
| `@ducanh2912/next-pwa` | 10.2 | Service Worker e manifest para PWA |

---

*Desenvolvido pelo Estagiário Ricardo Florentino Rodrigues em parceria com o Núcleo de Apoio à Gestão do HCFMB, Botucatu-SP*
