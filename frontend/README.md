# 📞 Aciono Você — Frontend Web/PWA

![Next.js](https://img.shields.io/badge/Next.js-black?style=flat&logo=next.js)
![React](https://img.shields.io/badge/React-20232A?style=flat&logo=react&logoColor=61DAFB)
![PWA](https://img.shields.io/badge/PWA-Ready-purple)

O frontend do Aciono Você é a interface do usuário focada na experiência em dispositivos móveis e desktops, desenvolvida para o HCFMB.

Ele provê a capacidade crítica do projeto: o **modo offline**. Médicos, enfermeiros e funcionários podem consultar ramais no aplicativo sem precisar de rede móvel ou Wi-Fi. Quando o usuário cria ou modifica contatos no modo offline, a aplicação salva essas ações localmente e as sincroniza com o servidor silenciosamente assim que o dispositivo recupera o acesso à internet.

## Funcionalidades e Demonstração

- **Acesso Offline Constante:** Os dados vivem no banco IndexedDB local (`LocalContato`) do navegador, alimentado pelo Dexie.js.
- **Live Queries:** Qualquer modificação local (ou via sincronização) é imediatamente refletida na tela usando `useLiveQuery`.
- **Instalável (PWA):** Manifesto e Service Worker nativos que permitem adicionar o site como app no celular.
- **Painel de Gestão:** Formulários fáceis de usar para gestão de ramais (institucionais ou públicos), acessíveis se o usuário logado tiver perfil de Gestor.
- **Indicador de Conexão:** Mostra aos usuários quando eles estão navegando offline e quantos itens restam ser sincronizados.

> *(Espaço reservado para capturas de tela ou um arquivo .gif demonstrando a aplicação em funcionamento)*

## Tecnologias

- **Plataforma:** Node.js
- **Framework Web:** Next.js 16 (App Router)
- **Biblioteca de UI:** React 19
- **Linguagem:** TypeScript 5
- **Banco de Dados Local:** Dexie.js 4.4 (Wrapper para IndexedDB)
- **Service Worker / PWA:** `@ducanh2912/next-pwa`
- **Estilos:** CSS Modules e componentes Lucide-React (ícones)

## Como Instalar e Executar

Se preferir rodar o frontend de maneira autônoma, em modo de desenvolvimento, siga os passos:

### Pré-requisitos
- Node.js (versão LTS recomendada, ex: 18 ou 20) instalado.
- NPM (incluso com o Node.js).
- Ter a API Backend rodando na porta 8085.

### Passo 1: Clonar o repositório
```bash
git clone https://github.com/seu-usuario/lista_telefonica_acionovoce.git
cd lista_telefonica_acionovoce/frontend
```

### Passo 2: Instalar as dependências
```bash
npm install
```

### Passo 3: Iniciar a aplicação
```bash
npm run dev
```
O servidor de desenvolvimento vai iniciar. Acesse o aplicativo através do navegador em `http://localhost:8086`.

Para testes do PWA (Service Workers normalmente não operam bem no modo de desenvolvimento), recomenda-se fazer a build de produção:
```bash
npm run build
npm run start
```
