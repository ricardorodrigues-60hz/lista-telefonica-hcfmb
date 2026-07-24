# Script de execução de testes e linters locais (Backend e Frontend)
$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " [1/4] Executando backend lint (poetry run task lint)..." -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan

Set-Location "$RootDir\backend"
poetry run task lint
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRO] Backend lint falhou!" -ForegroundColor Red
    Set-Location $RootDir
    exit 1
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " [2/4] Executando backend testes (poetry run task test)..." -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan

poetry run task test
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRO] Backend testes falharam!" -ForegroundColor Red
    Set-Location $RootDir
    exit 1
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " [3/4] Executando frontend lint (npm run lint)..." -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan

Set-Location "$RootDir\frontend"
npm run lint
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRO] Frontend lint falhou!" -ForegroundColor Red
    Set-Location $RootDir
    exit 1
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " [4/4] Executando frontend build (npm run build)..." -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan

npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRO] Frontend build falhou!" -ForegroundColor Red
    Set-Location $RootDir
    exit 1
}

Set-Location $RootDir

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Todos os testes e verificações passaram com sucesso!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
