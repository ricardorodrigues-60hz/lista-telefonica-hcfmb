# Script de deploy rápido via Docker Compose
$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " [1/2] Iniciando contêineres com Docker Compose..." -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan

docker-compose up -d --build

if ($LASTEXITCODE -eq 0) {
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host " [2/2] Contêineres iniciados com sucesso!" -ForegroundColor Green
    Write-Host " Backend API: http://localhost:8085/docs" -ForegroundColor Green
    Write-Host " Frontend PWA: http://localhost:8086" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Cyan
} else {
    Write-Host "[ERRO] Falha ao iniciar os contêineres!" -ForegroundColor Red
    exit 1
}
