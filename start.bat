@echo off
REM TraceAlign Lab local launcher (ASCII-safe for broken codepages)
cd /d "%~dp0"

echo ========================================
echo  TraceAlign Lab - Local Start
echo ========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python not found. Install Python 3.11+ and add to PATH.
  pause
  exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
  echo [ERROR] npm not found. Install Node.js and add to PATH.
  pause
  exit /b 1
)

if not exist ".env" (
  if exist ".env.example" copy /Y ".env.example" ".env" >nul
)

echo [1/6] Checking Python packages...
python -m pip install -r requirements.txt -q
if errorlevel 1 echo [WARN] pip install warning, continue...

if not exist "frontend\node_modules\" (
  echo [2/6] Installing frontend deps...
  pushd frontend
  call npm.cmd install
  if errorlevel 1 (
    echo [ERROR] npm install failed.
    pause
    exit /b 1
  )
  popd
) else (
  echo [2/6] Frontend deps OK.
)

echo [3/6] Start MCP tool server :8100
start "TraceAlign-MCP" /D "%~dp0" cmd.exe /k "python -m uvicorn mcp_servers.tool_server:app --host 127.0.0.1 --port 8100"

echo [4/6] Start backend :8000
start "TraceAlign-Backend" /D "%~dp0" cmd.exe /k "python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"

echo [5/6] Start frontend :3000
start "TraceAlign-Frontend" /D "%~dp0frontend" cmd.exe /k "npm.cmd run dev -- --host 127.0.0.1 --port 3000"

echo [6/6] Health checks...
set MCP_OK=0
set API_OK=0
set /a _h=0
:health_loop
set /a _h+=1
powershell -NoProfile -ExecutionPolicy Bypass -Command "try{$r=Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8100/mcp/health -TimeoutSec 1; if($r.StatusCode -ge 200){exit 0}else{exit 1}}catch{exit 1}" >nul 2>&1
if not errorlevel 1 set MCP_OK=1
powershell -NoProfile -ExecutionPolicy Bypass -Command "try{$r=Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/api/health -TimeoutSec 1; if($r.StatusCode -ge 200){exit 0}else{exit 1}}catch{exit 1}" >nul 2>&1
if not errorlevel 1 set API_OK=1
if %MCP_OK%==1 if %API_OK%==1 goto health_done
if %_h% GEQ 30 goto health_done
timeout /t 1 /nobreak >nul
goto health_loop

:health_done
if %MCP_OK%==1 (echo  [OK] MCP health http://127.0.0.1:8100/mcp/health) else (echo  [WARN] MCP not healthy yet - backend will fallback_local)
if %API_OK%==1 (echo  [OK] Backend health http://127.0.0.1:8000/api/health) else (echo  [WARN] Backend not healthy yet)

echo.
echo Waiting for http://127.0.0.1:3000 ...
set /a _n=0
:wait_loop
set /a _n+=1
powershell -NoProfile -ExecutionPolicy Bypass -Command "try{$r=Invoke-WebRequest -UseBasicParsing http://127.0.0.1:3000/ -TimeoutSec 1; if($r.StatusCode -ge 200){exit 0}else{exit 1}}catch{exit 1}" >nul 2>&1
if not errorlevel 1 goto open_browser
if %_n% GEQ 60 goto open_browser
timeout /t 1 /nobreak >nul
goto wait_loop

:open_browser
echo Opening browser via Edge/Chrome (skip broken default browser)...
call "%~dp0scripts\open_browser.cmd" "http://127.0.0.1:3000/"

echo.
echo ========================================
echo  MCP     : http://127.0.0.1:8100  health=%MCP_OK%
echo  Backend : http://127.0.0.1:8000  health=%API_OK%
echo  Frontend: http://127.0.0.1:3000
echo  Stop    : stop.bat  or  ????.vbs
echo ========================================
echo.
pause
