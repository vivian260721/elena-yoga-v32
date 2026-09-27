$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\backend"

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "[1/4] Creating Python 3.11 environment..."
    py -3.11 -m venv .venv
}

Write-Host "[2/4] Installing complete backend dependencies..."
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

Write-Host "[3/4] Verifying dependencies..."
.\.venv\Scripts\python.exe scripts\verify_install.py

Write-Host "[4/4] Starting Elena Yoga V3.1 backend..."
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
