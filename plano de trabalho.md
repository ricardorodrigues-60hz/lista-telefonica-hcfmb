# Planejamento do Projeto: Lista Telefônica PWA (Offline-First)

Este documento apresenta o planejamento estratégico, a arquitetura de dados e o mapeamento da stack tecnológica para o desenvolvimento de uma aplicação de Lista Telefônica funcional em modo offline, com sincronização automática posterior.

---

## 1. Stack Tecnológica Detalhada

Como o projeto será dividido em duas aplicações independentes rodando no mesmo servidor em portas distintas, a infraestrutura foi mapeada da seguinte forma:

### Frontend (Porta 3000 - Exemplo)
* **Framework Base:** Next.js (App Router)
* **Ecossistema PWA:** `@ducanh2912/next-pwa` (Configuração de Service Workers, Manifesto e estratégias de cache para os arquivos estáticos do Next.js).
* **Banco de Dados Local (Browser):** IndexedDB encapsulado pela biblioteca **Dexie.js** (fornece uma camada de abstração simples, baseada em Promises, para criar, ler, atualizar e deletar registros localmente).
* **Comunicação HTTP:** Axios ou Fetch API nativa.

### Backend (Porta 8000 - Exemplo)
* **Linguagem:** Python 3.11+
* **Framework API:** FastAPI ou Flask (FastAPI é altamente recomendado pela geração automática de documentação Swagger e excelente performance assíncrona).
* **Banco de Dados:** SQLite (Arquivo local `.db`).
* **ORM / Interface de Dados:** SQLAlchemy ou SQLModel (para mapeamento de tabelas e persistência estruturada).
* **Controle de Acesso:** CORS Middleware (configurado especificamente para permitir requisições originadas da porta do Frontend).

---

## 2. Estrutura do Banco de Dados (Esquema Unificado)

Para garantir que a sincronização funcione sem conflitos, o banco de dados local (IndexedDB) e o banco de dados remoto (SQLite) devem compartilhar da mesma estrutura lógica, com um detalhe crucial: o controle de estado de sincronização.

### Tabela: `contatos`
* **`id`** (Texto/UUID): Identificador único universal. *Nota: Usar UUID no cliente previne que dois registros gerados offline criem IDs numéricos duplicados.*
* **`nome`** (Texto): Nome do contato.
* **`telefone`** (Texto): Número de telefone com DDD.
* **`email`** (Texto, opcional): Endereço de e-mail.
* **`tipo_numero`** (Texto/Enum): Flag para categorização do número (`institucional` ou `publico`).
* **`atualizado_em`** (Timestamp): Data e hora da última modificação do registro.
* **`sincronizado`** (Booleano - *Apenas no IndexedDB*): Flag que indica se a alteração local já foi enviada com sucesso para o servidor Python (`true` ou `false`).
* **`excluido`** (Booleano): Flag de exclusão lógica (soft delete). Essencial para replicar deleções feitas em modo offline.

---

## 3. Arquitetura de Sincronização (Fluxo de Trabalho)

O núcleo do funcionamento Offline-First desta aplicação baseia-se em decisões locais imediatas e sincronização em segundo plano.

### Cenário A: Operação Online (Fluxo Padrão)
1. O usuário abre o app. O Next.js carrega a interface (muitas vezes direto do cache do Service Worker).
2. O frontend faz uma requisição `GET /contatos` para o backend Python.
3. Os dados recebidos do SQLite atualizam o IndexedDB local.
4. A interface exibe os dados do IndexedDB (Garantia de renderização instantânea).

### Cenário B: Criação/Edição Offline
1. O usuário preenche o formulário e clica em "Salvar".
2. O frontend intercepta o envio e detecta a ausência de rede (ou tenta a API e recebe timeout).
3. O registro é salvo no **IndexedDB** local com um `id` gerado via UUID, `sincronizado: false` e o timestamp atual.
4. A interface do usuário é atualizada imediatamente usando os dados do IndexedDB (o usuário vê o contato na lista com um ícone visual de "Pendente de Sincronização").

### Cenário C: O Processo de Sincronização (Reconexão)
1. O Service Worker (via Background Sync API ou um listener de eventos `online` no Next.js) detecta o retorno da conexão com a internet.
2. O frontend executa uma rotina de varredura no IndexedDB: `Dexie.contatos.where('sincronizado').equals(false)`.
3. Para cada registro pendente encontrado:
    * O frontend envia um payload de sincronização para o backend Python (`POST /api/sync`).
    * O backend Python recebe o JSON, verifica o UUID. Se o UUID já existir no SQLite, ele compara o `atualizado_em` e atualiza se o dado do cliente for mais recente. Se não existir, insere o novo registro.
    * O backend responde com `status: 200 OK`.
4. Ao receber a confirmação de sucesso do servidor, o frontend altera a flag no IndexedDB para `sincronizado: true` e remove o alerta visual da tela.

---

## 4. Endpoints Essenciais do Backend (Python)

O backend precisa expor uma API simples e direta para suprir a demanda de sincronização em lote ou individual:

* **`GET /api/contatos`**: Retorna a lista completa de contatos ativos do SQLite para carga inicial do PWA.
* **`POST /api/sync`**: Endpoint inteligente. Recebe um array de contatos (novos ou modificados). Processa inserções e atualizações baseadas em UUID e retorna a lista de IDs confirmados com sucesso.
* **`POST /api/contatos/deletar`**: Recebe um ID para marcar o contato como excluído ou processar a deleção física.

---

## 5. Estrutura de Pastas Sugerida

Para manter a organização com os dois ambientes rodando no mesmo servidor:

```text
lista-telefonica-pwa/
│
├── backend/               # Aplicação Python
│   ├── main.py            # Ponto de entrada (FastAPI/Flask)
│   ├── database.py        # Configuração do SQLite e SQLAlchemy
│   ├── models.py          # Modelos de dados
│   ├── schemas.py         # Validação de dados (Pydantic, se FastAPI)
│   └── lista.db           # Arquivo local do banco SQLite
│
└── frontend/              # Aplicação Next.js
    ├── src/
    │   ├── app/           # Rotas e páginas (App Router)
    │   ├── components/    # Componentes de UI (Lista, Formulário)
    │   └── db/            # Configuração do Dexie.js (IndexedDB)
    ├── public/            # Manifesto do PWA, ícones e assets
    ├── next.config.mjs    # Configuração do @ducanh2912/next-pwa
    └── package.json       # Dependências do Node