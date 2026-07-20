@echo off
REM Open URL with Edge/Chrome explicitly. Avoids broken Quark/default browser association.
set "URL=%~1"
if "%URL%"=="" set "URL=http://127.0.0.1:3000/"

if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" (
  start "" "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" "%URL%"
  exit /b 0
)
if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" (
  start "" "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" "%URL%"
  exit /b 0
)
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (
  start "" "%ProgramFiles%\Google\Chrome\Application\chrome.exe" "%URL%"
  exit /b 0
)
if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" (
  start "" "%LocalAppData%\Google\Chrome\Application\chrome.exe" "%URL%"
  exit /b 0
)

REM Last resort: explorer + URL often still uses broken handler; try rundll32
rundll32 url.dll,FileProtocolHandler %URL%
exit /b 0
