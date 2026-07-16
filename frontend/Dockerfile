FROM node:20-alpine AS builder
WORKDIR /app

# Install dependencies and build
COPY package*.json ./
RUN npm ci --legacy-peer-deps
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

# Copy only what is needed to run
COPY --from=builder /app/.next .next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/node_modules ./node_modules

ENV PORT=8086
EXPOSE 8086

CMD ["npm", "run", "start"]