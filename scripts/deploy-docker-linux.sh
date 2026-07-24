#!/bin/bash

echo "============================================================"
echo "[1/2] Iniciando conteineres com Docker Compose..."
echo "============================================================"

# Executa o docker compose (usa 'docker compose' moderno, compatível com Linux)
docker compose up -d --build

# Verifica se o comando anterior falhou (status diferente de 0)
if [ $? -ne 0 ]; then
    echo "[ERRO] Falha ao iniciar os conteineres!"
    exit 1
fi

echo "============================================================"
echo "[2/2] Conteineres iniciados com sucesso!"
echo "Backend API: http://localhost:8085/docs"
echo "Frontend PWA: http://localhost:8086"
echo "============================================================"
