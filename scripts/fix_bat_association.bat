@echo off
REM Optional fix for broken Windows .bat association (needs Admin once).
echo Current batfile association:
ftype batfile
echo.
echo Will set to: %%SystemRoot%%\System32\cmd.exe /c "%%1" %%*
echo.
pause
ftype batfile="%SystemRoot%\System32\cmd.exe" /c "%1" %*
assoc .bat=batfile
echo.
echo Done. Try double-click start.bat again.
pause
