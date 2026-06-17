@echo off
title Lista Telefonica AcionoVoce

rem Start backend server on port 8085
start "Backend" cmd /k "cd /d %~dp0backend && .\venv\Scripts\python -m uvicorn main:app --host 127.0.0.1 --port 8085"

rem Start frontend dev server on port 8086
start "Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
