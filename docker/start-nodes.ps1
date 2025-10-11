# PowerShell script para iniciar nodos Link-Chat en terminales separadas
# Este script inicia cada nodo en su propia ventana de terminal

Write-Host "=== Iniciando Link-Chat Docker Nodes ===" -ForegroundColor Cyan
Write-Host ""

# Verificar que Docker está corriendo
$dockerRunning = docker info 2>$null
if (-not $dockerRunning) {
    Write-Host "ERROR: Docker no está corriendo. Por favor inicia Docker Desktop." -ForegroundColor Red
    exit 1
}

# Navegar al directorio docker
$scriptPath = Split-Path -Parent $MyInvocation.MyInvocation.MyCommand.Path
Set-Location $scriptPath

Write-Host "1. Construyendo contenedores..." -ForegroundColor Yellow
docker-compose build

Write-Host ""
Write-Host "2. Iniciando contenedores en modo detached..." -ForegroundColor Yellow
docker-compose up -d

Write-Host ""
Write-Host "3. Esperando que los contenedores estén listos..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "4. Abriendo terminales interactivas para cada nodo..." -ForegroundColor Yellow

# Abrir terminal para Node 1
Write-Host "   - Abriendo terminal para Node 1..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "Write-Host '=== Link-Chat Node 1 ===' -ForegroundColor Cyan; docker exec -it linkchat-node1 bash"

Start-Sleep -Seconds 1

# Abrir terminal para Node 2
Write-Host "   - Abriendo terminal para Node 2..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "Write-Host '=== Link-Chat Node 2 ===' -ForegroundColor Cyan; docker exec -it linkchat-node2 bash"

Start-Sleep -Seconds 1

# Abrir terminal para Node 3
Write-Host "   - Abriendo terminal para Node 3..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "Write-Host '=== Link-Chat Node 3 ===' -ForegroundColor Cyan; docker exec -it linkchat-node3 bash"

Write-Host ""
Write-Host "=== Todos los nodos iniciados ===" -ForegroundColor Green
Write-Host ""
Write-Host "Comandos útiles:" -ForegroundColor Yellow
Write-Host "  - Para detener: docker-compose down" -ForegroundColor White
Write-Host "  - Para ver logs: docker-compose logs -f" -ForegroundColor White
Write-Host "  - Para reiniciar: docker-compose restart" -ForegroundColor White
Write-Host ""
Write-Host "Dentro de cada contenedor, ejecuta:" -ForegroundColor Yellow
Write-Host "  sudo python main.py" -ForegroundColor White
Write-Host ""
