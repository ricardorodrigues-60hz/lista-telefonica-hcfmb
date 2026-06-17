@echo off
title Parar Servidores - Lista Telefonica AcionoVoce

echo Parando os servidores do backend (FastAPI - porta 8085) e frontend (Next.js - porta 8086)...

rem Encontra e encerra processos escutando na porta 8085 (Backend)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8085 ^| findstr LISTENING') do (
    echo Encerrando processo na porta 8085 (PID: %%a)...
    taskkill /PID %%a /F
)

rem Encontra e encerra processos escutando na porta 8086 (Frontend)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8086 ^| findstr LISTENING') do (
    echo Encerrando processo na porta 8086 (PID: %%a)...
    taskkill /PID %%a /F
)

rem Backup genérico por nome de processo caso restem sobreviventes
echo Limpando eventuais processos de node ou uvicorn residuais...
taskkill /f /im node.exe 2>nul
taskkill /f /im python.exe 2>nul

echo.
echo Servidores parados com sucesso!
pause
