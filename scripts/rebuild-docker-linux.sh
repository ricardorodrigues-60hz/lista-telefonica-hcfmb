#!/bin/bash

echo "============================================================"
echo "[1/3] Parando e removendo conteineres e volumes..."
echo "============================================================"
docker compose down -v

echo "============================================================"
echo "[2/3] Reconstruindo imagens sem cache..."
echo "============================================================"
docker compose build --no-cache

if [ $? -ne 0 ]; then
    echo "[ERRO] Falha na reconstrucao das imagens!"
    exit 1
fi

echo "============================================================"
echo "[3/3] Subindo conteineres..."
echo "============================================================"
docker compose up -d

if [ $? -ne 0 ]; then
    echo "[ERRO] Falha ao subir os conteineres!"
    exit 1
fi

echo "============================================================"
echo "Reconstrucao concluida com sucesso!"
echo "Backend API: http://localhost:8085/docs"
echo "Frontend PWA: http://localhost:8086"
echo "============================================================"
