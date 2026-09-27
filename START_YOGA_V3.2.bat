@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo Elena Yoga V3.2 - One Click Start
echo ==========================================

if not exist "backend\.venv\Scripts\python.exe" (
  echo [1/4] Creating Python 3.11 environment...
  py -3.11 -m venv backend\.venv || goto :error
  echo [2/4] Installing backend packages...
  backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt || goto :error
  echo [3/4] Installing frontend packages...
  backend\.venv\Scripts\python.exe -m pip install -r frontend\requirements.txt || goto :error
) else (
  echo [1/4] Existing environment found.
  echo [2/4] Checking required packages...
  backend\.venv\Scripts\python.exe backend\scripts\verify_install.py || (
    echo Repairing backend packages...
    backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt || goto :error
  )
  backend\.venv\Scripts\python.exe -c "import nicegui,httpx" >nul 2>&1 || (
    echo Repairing frontend packages...
    backend\.venv\Scripts\python.exe -m pip install -r frontend\requirements.txt || goto :error
  )
)

echo [4/4] Starting backend and frontend...
start "Elena Yoga V3.2 Backend" cmd /k "cd /d "%~dp0backend" && .venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"
timeout /t 3 /nobreak >nul
start "Elena Yoga V3.2 Frontend" cmd /k "cd /d "%~dp0frontend" && ..\backend\.venv\Scripts\python.exe main.py"
timeout /t 3 /nobreak >nul
start "" http://localhost:8080
exit /b 0

:error
echo.
echo Setup failed. Please keep this window open and take a screenshot of the error.
pause
exit /b 1
