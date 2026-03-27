[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Krisha Parser Bot - Zapusk" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path "venv")) {
    Write-Host "venv ne najden! Snachala zapustite: .\setup.ps1" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "wa-server\node_modules")) {
    Write-Host "Node zavisimosti ne ustanovleny! Snachala: .\setup.ps1" -ForegroundColor Red
    exit 1
}

# Zapusk WA-servera v fone
Write-Host "[1/2] Zapuskaem WhatsApp server..." -ForegroundColor Yellow
$waProcess = Start-Process -FilePath "node" -ArgumentList "server.js" -WorkingDirectory "wa-server" -PassThru -WindowStyle Minimized
Write-Host "  WA-server zapushchen (PID: $($waProcess.Id), port 3457)" -ForegroundColor Green
Start-Sleep -Seconds 3

# Zapusk GUI
Write-Host "[2/2] Zapuskaem GUI..." -ForegroundColor Yellow
Write-Host ""
& .\venv\Scripts\Activate.ps1
python main.py

# Kogda GUI zakroetsya - ubivaem WA-server
Write-Host ""
Write-Host "Zavershaem WA-server..." -ForegroundColor Yellow
try {
    Stop-Process -Id $waProcess.Id -Force -ErrorAction SilentlyContinue
} catch {}
Write-Host "Vsyo ostanovleno. Do vstrechi!" -ForegroundColor Green
