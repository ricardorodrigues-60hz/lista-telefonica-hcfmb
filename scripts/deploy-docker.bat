@echo off
echo ============================================================
echo [1/2] Iniciando conteineres com Docker Compose...
echo ============================================================
docker-compose up -d --build
if errorlevel 1 (
    echo [ERRO] Falha ao iniciar os conteineres!
    exit /b 1
)

echo ============================================================
echo [2/2] Conteineres iniciados com sucesso!
echo Backend API: http://localhost:8085/docs
echo Frontend PWA: http://localhost:8086
echo ============================================================
