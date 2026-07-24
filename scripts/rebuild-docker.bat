@echo off
echo ============================================================
echo [1/3] Parando e removendo conteineres e volumes...
echo ============================================================
docker-compose down -v

echo ============================================================
echo [2/3] Reconstruindo imagens sem cache...
echo ============================================================
docker-compose build --no-cache
if errorlevel 1 (
    echo [ERRO] Falha na reconstrucao das imagens!
    exit /b 1
)

echo ============================================================
echo [3/3] Subindo conteineres...
echo ============================================================
docker-compose up -d
if errorlevel 1 (
    echo [ERRO] Falha ao subir os conteineres!
    exit /b 1
)

echo ============================================================
echo Reconstrucao concluida com sucesso!
echo Backend API: http://localhost:8085/docs
echo Frontend PWA: http://localhost:8086
echo ============================================================
