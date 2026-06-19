# Lista Telefônica AcionoVocê 📞

Aplicação offline-first com sincronização bidirecional de dados desenvolvida para gerenciamento eficiente de ramais e contatos internos.

## 🚀 Arquitetura do Projeto

O projeto é dividido em duas partes principais:

1. **Backend (`/backend`)**:
   - Desenvolvido em **Python FastAPI**.
   - Banco de dados **SQLite** integrado para facilidade de deployment local.
   - Autenticação e Autorização via tokens JWT e criptografia de senhas usando `bcrypt`.
   - APIs REST para sincronização inteligente e trilhas de auditoria das alterações.

2. **Frontend (`/frontend`)**:
   - Desenvolvido em **Next.js** (App Router).
   - Armazenamento offline local utilizando **IndexedDB** gerenciado pela biblioteca **Dexie.js**.
   - Interface premium projetada com Vanilla CSS baseada no guia de estilo (Design System) da marca.
   - Suporte PWA para instalação como aplicativo nativo em dispositivos móveis e desktops.

---

## 🛠️ Requisitos e Tecnologias

### Backend
- Python 3.10 ou superior
- FastAPI
- Uvicorn
- SQLAlchemy
- Bcrypt (para hash de senhas de forma segura)
- Python-Jose (para geração de tokens JWT)
- Pydantic v2 (com suporte a validação de e-mails)

### Frontend
- Node.js 18 ou superior
- Next.js 16
- React 19
- Dexie.js (para gerenciamento de IndexedDB local)
- Lucide React (pacote de ícones premium)

---

## 📥 Instalação e Configuração

### 1. Clonando o Repositório
```bash
git clone <URL_DO_REPOSITORIO>
cd lista_telefonica_acionovoce
```

### 2. Configurando o Backend
```bash
cd backend
# Crie o ambiente virtual
python -m venv venv
# Ative o ambiente virtual (Windows)
.\venv\Scripts\activate
# Instale as dependências
pip install -r requirements.txt
```

### 3. Configurando o Frontend
```bash
cd ../frontend
# Instale as dependências do Node.js
npm install
```

---

## ⚡ Como Executar a Aplicação (Windows)

Na raiz do projeto existem dois scripts batch criados para simplificar o controle dos servidores:

- **Para Iniciar os Servidores:** Execute o arquivo [**`start.bat`**](file:///C:/Users/rrodrigues/Documents/ObsidianVault/01_Servi%C3%A7o/01_Projetos/02_Trabalho/lista_telefonica_acionovoce/start.bat) com duplo clique ou via terminal.
  - Ele irá abrir os servidores locais nas portas especificadas:
    - **Backend (FastAPI):** `http://localhost:8085` (ou no IP de rede para acesso de outros dispositivos: `http://0.0.0.0:8085`).
    - **Frontend (Next.js):** `http://localhost:8086`.

- **Para Parar os Servidores:** Execute o arquivo [**`stop.bat`**](file:///C:/Users/rrodrigues/Documents/ObsidianVault/01_Servi%C3%A7o/01_Projetos/02_Trabalho/lista_telefonica_acionovoce/stop.bat) para encerrar as instâncias rodando e liberar as portas `8085` e `8086`.

---

**Com Docker Compose (iniciar / parar servidores):**

- **Iniciar servidores (em background, rebuild opcional):**

```bash
docker compose up -d --build
```

- **Parar e remover containers/recursos:**

```bash
docker compose down
```

## 🔐 Contas Padrão para Teste (Criadas automaticamente na inicialização)

- **Gestor (Permissões de Escrita, Edição e Exclusão):**
  - **E-mail:** `gestor@hcfmb.unesp.br`
  - **Senha:** `gestor123`

- **Consultor (Acesso a visualização e busca):**
  - **E-mail:** `consultor@hcfmb.unesp.br`
  - **Senha:** `consultor123`