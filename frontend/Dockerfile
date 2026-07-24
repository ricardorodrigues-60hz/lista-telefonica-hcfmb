# Stage 1: Builder & Dependencies
FROM node:20-alpine AS deps

WORKDIR /app

COPY package*.json ./

RUN npm ci --only=production && \
    npm cache clean --force

# Stage 2: Build
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./

RUN npm ci && \
    npm cache clean --force

COPY . .

RUN npm run build

# Stage 3: Runtime
FROM node:20-alpine

WORKDIR /app

ENV NODE_ENV=production \
    PORT=8086 \
    NEXT_TELEMETRY_DISABLED=1

# Copia arquivos necessários para produção
COPY --from=deps /app/node_modules ./node_modules
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public

EXPOSE 8086

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:8086 || exit 1

CMD ["npm", "run", "start"]
