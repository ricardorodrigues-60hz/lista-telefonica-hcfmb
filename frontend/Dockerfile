# 1. Imagem base oficial do Node
FROM node:20-alpine

WORKDIR /app

# 2. Copia os arquivos de definição de dependências
COPY package*.json ./

# 3. Instala as dependências do projeto
RUN npm install

# 4. Copia o restante do código do Next.js
COPY . .

# Executa o build de produção do Next.js
RUN npm run build

EXPOSE 8086

# 5. Define a porta do Next.js via variável de ambiente antes de rodar
ENV PORT=8086

CMD ["npm", "run", "start"]