@echo off
set "ROOT_DIR=%~dp0.."

echo ============================================================
echo [1/4] Executando backend lint (poetry run task lint)...
echo ============================================================
cd /d "%ROOT_DIR%\backend"
call poetry run task lint
if errorlevel 1 (
    echo [ERRO] Backend lint falhou!
    exit /b 1
)

echo ============================================================
echo [2/4] Executando backend testes (poetry run task test)...
echo ============================================================
call poetry run task test
if errorlevel 1 (
    echo [ERRO] Backend testes falharam!
    exit /b 1
)

echo ============================================================
echo [3/4] Executando frontend lint (npm run lint)...
echo ============================================================
cd /d "%ROOT_DIR%\frontend"
call npm run lint
if errorlevel 1 (
    echo [ERRO] Frontend lint falhou!
    exit /b 1
)

echo ============================================================
echo [4/4] Executando frontend build (npm run build)...
echo ============================================================
call npm run build
if errorlevel 1 (
    echo [ERRO] Frontend build falhou!
    exit /b 1
)

cd /d "%ROOT_DIR%"
echo ============================================================
echo Todos os testes e verificacoes passaram com sucesso!
echo ============================================================
