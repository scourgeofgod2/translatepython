# CLI smoke: translate a sample PDF via pdf2zh with env from data/.env
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Pdf = $args[0]
if (-not $Pdf) {
    $Pdf = "samples\sample.pdf"
}
if (-not (Test-Path $Pdf)) {
    Write-Host "PDF not found: $Pdf" -ForegroundColor Red
    Write-Host "Usage: .\scripts\smoke_translate.ps1 path\to\file.pdf"
    exit 1
}

# Load data/.env
if (Test-Path "data\.env") {
    Get-Content "data\.env" | ForEach-Object {
        if ($_ -match '^\s*([^#=]+)=(.*)$') {
            [Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim(), "Process")
        }
    }
}

if (-not $env:OPENAI_API_KEY -or $env:OPENAI_API_KEY -eq "sk-your-key-here") {
    Write-Host "Set OPENAI_API_KEY in data\.env first." -ForegroundColor Red
    exit 1
}
if (-not $env:OPENAI_BASE_URL) { $env:OPENAI_BASE_URL = "https://app.claude.gg/v1" }
if (-not $env:OPENAI_MODEL) { $env:OPENAI_MODEL = "claude-sonnet-4-6" }

# Ensure /v1 suffix
if ($env:OPENAI_BASE_URL -notmatch '/v1/?$') {
    $env:OPENAI_BASE_URL = $env:OPENAI_BASE_URL.TrimEnd('/') + '/v1'
}

$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
if (-not $env:HF_ENDPOINT) { $env:HF_ENDPOINT = "https://hf-mirror.com" }

$OutDir = "samples\out"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

Write-Host "Translating $Pdf → $OutDir (EN→TR) via $($env:OPENAI_BASE_URL) model=$($env:OPENAI_MODEL)" -ForegroundColor Cyan

uv run --system-certs pdf2zh $Pdf -li en -lo tr -s openai -t 4 --prompt "prompts\tr_scientific.txt" -o $OutDir

Write-Host ""
Write-Host "Done. Look for *-mono.pdf in $OutDir" -ForegroundColor Green
