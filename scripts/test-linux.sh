#!/bin/bash

# Define a pasta raiz (um nível acima de onde o script está guardado)
ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)

echo "============================================================"
echo "[1/4] Executando backend lint (poetry run task lint)..."
echo "============================================================"
cd "$ROOT_DIR/backend" || exit 1
poetry run task lint

if [ $? -ne 0 ]; then
    echo "[ERRO] Backend lint falhou!"
    exit 1
fi

echo "============================================================"
echo "[2/4] Executando backend testes (poetry run task test)..."
echo "============================================================"
poetry run task test

if [ $? -ne 0 ]; then
    echo "[ERRO] Backend testes falharam!"
    exit 1
fi

echo "============================================================"
echo "[3/4] Executando frontend lint (npm run lint)..."
echo "============================================================"
cd "$ROOT_DIR/frontend" || exit 1
npm run lint

if [ $? -ne 0 ]; then
    echo "[ERRO] Frontend lint falhou!"
    exit 1
fi

echo "============================================================"
echo "[4/4] Executando frontend build (npm run build)..."
echo "============================================================"
npm run build

if [ $? -ne 0 ]; then
    echo "[ERRO] Frontend build falhou!"
    exit 1
fi

cd "$ROOT_DIR" || exit 1
echo "============================================================"
echo "Todos os testes e verificacoes passaram com sucesso!"
echo "============================================================"
