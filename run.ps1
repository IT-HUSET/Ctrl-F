# Ctrl-F — one command to run the prototype.
#   .\run.ps1            build anything missing, then open the app
#   .\run.ps1 -Rebuild   redo OCR and extraction from scratch
param([switch]$Rebuild)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if ($Rebuild) { Remove-Item -Recurse -Force cache -ErrorAction SilentlyContinue }

Write-Host "==> dependencies" -ForegroundColor Cyan
uv sync --quiet

$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) { $ollama = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" }
if (-not (Get-Process ollama -ErrorAction SilentlyContinue)) {
    Write-Host "==> starting local model server" -ForegroundColor Cyan
    Start-Process -FilePath $ollama -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 4
}

if (-not (Test-Path cache/pages.jsonl)) {
    Write-Host "==> OCR over the corpus (a few minutes, once)" -ForegroundColor Cyan
    uv run python -m src.ctrlf.ingest
}
if (-not (Test-Path cache/records.json)) {
    Write-Host "==> extracting findings with the local model" -ForegroundColor Cyan
    uv run python -m src.ctrlf.extract
}

if (-not (Test-Path cache/embeddings.json)) {
    Write-Host "==> building the semantic index" -ForegroundColor Cyan
    uv run python -m src.ctrlf.embed
}

Write-Host "==> scoring against the labelled set" -ForegroundColor Cyan
uv run python -m src.ctrlf.eval

Write-Host "==> opening the app" -ForegroundColor Cyan
uv run streamlit run app.py
