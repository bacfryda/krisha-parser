[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Krisha Parser Bot - Ustanovka" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Proverka Python
try {
    $pyVer = python --version 2>&1
    Write-Host "Python: $pyVer" -ForegroundColor Green
} catch {
    Write-Host "Python ne najden! Ustanovite Python 3.10+ s python.org" -ForegroundColor Red
    exit 1
}

# Proverka Node.js
try {
    $nodeVer = node --version 2>&1
    Write-Host "Node.js: $nodeVer" -ForegroundColor Green
} catch {
    Write-Host "Node.js ne najden! Ustanovite Node.js 18+ s nodejs.org" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Python venv
Write-Host "[1/4] Sozdaem virtualnoe okruzhenie Python..." -ForegroundColor Yellow
if (-not (Test-Path "venv")) {
    python -m venv venv
    Write-Host "  venv sozdan" -ForegroundColor Green
} else {
    Write-Host "  venv uzhe sushchestvuet" -ForegroundColor Gray
}

# Aktiviruem i stavim zavisimosti
Write-Host "[2/4] Ustanavlivaem Python zavisimosti..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip 2>$null
pip install -r requirements.txt
Write-Host "  Python zavisimosti ustanovleny" -ForegroundColor Green
Write-Host ""

# Node.js zavisimosti
Write-Host "[3/4] Ustanavlivaem Node.js zavisimosti (wa-server)..." -ForegroundColor Yellow
Push-Location wa-server
npm install
Pop-Location
Write-Host "  Node.js zavisimosti ustanovleny" -ForegroundColor Green
Write-Host ""

# Init DB
Write-Host "[4/4] Inicializaciya bazy dannyh..." -ForegroundColor Yellow
python -c "from database import init_db; init_db(); print('  Baza dannyh gotova')"
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Ustanovka zavershena!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Dlya zapuska: .\start.ps1" -ForegroundColor White
Write-Host ""
