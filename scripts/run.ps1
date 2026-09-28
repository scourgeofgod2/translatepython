$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

uv run --system-certs uvicorn backend.app.main:app --host 127.0.0.1 --port 8765 --reload
