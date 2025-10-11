# PowerShell script para detener los nodos Link-Chat

Write-Host "=== Deteniendo Link-Chat Docker Nodes ===" -ForegroundColor Cyan
Write-Host ""

# Navegar al directorio docker
$scriptPath = Split-Path -Parent $MyInvocation.MyInvocation.MyCommand.Path
Set-Location $scriptPath

Write-Host "Deteniendo y eliminando contenedores..." -ForegroundColor Yellow
docker-compose down

Write-Host ""
Write-Host "=== Contenedores detenidos ===" -ForegroundColor Green
Write-Host ""
Write-Host "Las terminales interactivas se cerrarán automáticamente." -ForegroundColor White
Write-Host ""
