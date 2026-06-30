@echo off
REM Script para subir os servidores via Docker Compose e abrir o frontend/backend
cd /d %~dp0
echo Building and starting containers with Docker Compose...
docker compose up -d --build
if %errorlevel% neq 0 (
  echo Docker compose failed. Press any key to continue...
  pause
  exit /b %errorlevel%
)
echo Opening frontend and backend in browser...
start http://localhost:8086
start http://localhost:8085/docs
echo All done.
exit /b 0
