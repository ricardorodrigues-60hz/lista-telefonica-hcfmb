# Script de reconstrução limpa do ambiente Docker
$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " [1/3] Parando e removendo contêineres e volumes antigos..." -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan

docker-compose down -v

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " [2/3] Reconstruindo imagens sem cache..." -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan

docker-compose build --no-cache

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRO] Falha ao construir as imagens Docker!" -ForegroundColor Red
    exit 1
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " [3/3] Subindo novos contêineres..." -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan

docker-compose up -d

if ($LASTEXITCODE -eq 0) {
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host " Reconstrução e inicialização concluídas com sucesso!" -ForegroundColor Green
    Write-Host " Backend API: http://localhost:8085/docs" -ForegroundColor Green
    Write-Host " Frontend PWA: http://localhost:8086" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Cyan
} else {
    Write-Host "[ERRO] Falha ao subir os contêineres!" -ForegroundColor Red
    exit 1
}
