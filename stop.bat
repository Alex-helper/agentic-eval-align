@echo off
cd /d "%~dp0"
echo Stopping TraceAlign ports 8100 / 8000 / 3000 ...

for %%P in (8100 8000 3000) do (
  for /f "tokens=5" %%A in ('netstat -ano ^| findstr ":%%P " ^| findstr "LISTENING"') do (
    echo kill PID %%A port %%P
    taskkill /PID %%A /F >nul 2>&1
  )
)

taskkill /FI "WINDOWTITLE eq TraceAlign-MCP*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq TraceAlign-Backend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq TraceAlign-Frontend*" /F >nul 2>&1

echo Done.
pause
