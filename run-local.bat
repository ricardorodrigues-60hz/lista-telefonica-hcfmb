@echo off
REM run-local.bat - inicia backend e frontend localmente em janelas separadas (sem Docker)

cd /d %~dp0

REM Start backend in a new cmd window using uvicorn
start "Backend (uvicorn)" cmd /k "cd /d "%~dp0backend" && echo Starting backend on http://127.0.0.1:8085 && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8085"

REM Start frontend in a new cmd window using npm
start "Frontend (Next.js)" cmd /k "cd /d "%~dp0frontend" && echo Starting frontend on http://localhost:8086 && npm run dev"

REM Small delay then open both in the default browser
timeout /t 3 /nobreak >nul
start http://localhost:8086
start http://127.0.0.1:8085/docs

exit /b 0
