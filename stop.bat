@echo off
echo Stopping FinPilot servers (ports 8000 and 3000)...
for %%P in (8000 3000) do (
  for /f "tokens=5" %%I in ('netstat -ano ^| findstr ":%%P " ^| findstr LISTENING') do (
    taskkill /PID %%I /T /F >nul 2>&1
  )
)
echo Done.
timeout /t 2 /nobreak >nul
