@echo off
setlocal
title FinPilot AI Launcher
cd /d "%~dp0"

echo ============================================
echo   FinPilot AI - backend + frontend launcher
echo ============================================

where python >nul 2>&1
if errorlevel 1 goto nopython
where npm >nul 2>&1
if errorlevel 1 goto nonode

REM ---- refuse to start if old servers still hold the ports ----
netstat -ano | findstr ":8000 " | findstr LISTENING >nul 2>&1
if not errorlevel 1 goto portbusy
netstat -ano | findstr ":3000 " | findstr LISTENING >nul 2>&1
if not errorlevel 1 goto portbusy

REM ---- backend: use the venv if it works, otherwise (re)build it ----
if not exist "backend\venv\Scripts\python.exe" goto makevenv
"backend\venv\Scripts\python.exe" -c "import fastapi, uvicorn, jose, multipart" >nul 2>&1
if errorlevel 1 goto makevenv
goto venvok

:makevenv
echo [setup] Building backend virtual environment (first run, or the folder was moved)...
if exist "backend\venv" rmdir /s /q "backend\venv"
python -m venv "backend\venv"
if errorlevel 1 goto venvfail
"backend\venv\Scripts\python.exe" -m pip install --upgrade pip
"backend\venv\Scripts\python.exe" -m pip install -r "backend\requirements.txt"
if errorlevel 1 goto pipfail

:venvok
REM ---- frontend: install packages if missing ----
if exist "frontend\node_modules\next" goto nodeok
echo [setup] Installing frontend packages (first run)...
pushd frontend
call npm install
popd
if not exist "frontend\node_modules\next" goto npmfail

:nodeok
echo [run] Starting backend  (http://127.0.0.1:8000) ...
start "FinPilot Backend" /D "backend" cmd /k ""venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

echo [run] Starting frontend (http://localhost:3000) ...
start "FinPilot Frontend" /D "frontend" cmd /k "npm run dev"

echo [wait] Waiting for the backend...
call :waitfor http://127.0.0.1:8000/health
if errorlevel 1 goto backendfail

echo [wait] Waiting for the frontend (first start compiles, can take 30-60s)...
call :waitfor http://127.0.0.1:3000
if errorlevel 1 goto frontendfail

echo.
echo  READY  -  opening http://localhost:3000
echo  Login: owner@aaravretail.com / demo1234
start http://localhost:3000
echo.
echo  API docs: http://127.0.0.1:8000/docs
echo  To stop everything, run stop.bat
echo.
pause
exit /b 0

:waitfor
powershell -NoProfile -Command "for($i=0;$i -lt 90;$i++){ try { $null = Invoke-WebRequest -UseBasicParsing '%~1' -TimeoutSec 2; exit 0 } catch { Start-Sleep -Seconds 1 } }; exit 1"
exit /b %errorlevel%

:nopython
echo ERROR: Python was not found. Install Python 3.10+ from python.org and tick "Add python.exe to PATH".
goto fail
:nonode
echo ERROR: Node.js / npm was not found. Install Node 18+ from nodejs.org.
goto fail
:portbusy
echo ERROR: Port 8000 or 3000 is already in use - an old server is still running.
echo        Run stop.bat first, then start.bat again.
goto fail
:venvfail
echo ERROR: Could not create the Python virtual environment.
goto fail
:pipfail
echo ERROR: Installing backend requirements failed - read the messages above.
goto fail
:npmfail
echo ERROR: npm install failed - read the messages above.
goto fail
:backendfail
echo ERROR: The backend did not come up. Look at the "FinPilot Backend" window for the error.
goto fail
:frontendfail
echo ERROR: The frontend did not come up. Look at the "FinPilot Frontend" window for the error.
goto fail
:fail
echo.
pause
exit /b 1
