# mirapdf setup — Python 3.12 + uv + deps
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> Checking uv..." -ForegroundColor Cyan
$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
$uv = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uv) {
    Write-Host "Installing uv..." -ForegroundColor Yellow
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
    $uv = Get-Command uv -ErrorAction SilentlyContinue
    if (-not $uv) {
        Write-Host "uv not found after install. Try: winget install astral-sh.uv" -ForegroundColor Red
        exit 1
    }
}

Write-Host "==> Installing Python 3.12..." -ForegroundColor Cyan
uv python install 3.12

Write-Host "==> Syncing project dependencies..." -ForegroundColor Cyan
uv sync --system-certs

Write-Host "==> Creating data directories..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path "data", "data/jobs" | Out-Null

if (-not (Test-Path "data\.env")) {
    Copy-Item ".env.example" "data\.env"
    Write-Host "Created data/.env — put your API key there." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Next steps:"
Write-Host "  1. Edit data/.env  (OPENAI_API_KEY)"
Write-Host "  2. .\scripts\run.ps1"
Write-Host "  3. Open http://127.0.0.1:8765/"
