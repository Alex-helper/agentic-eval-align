' Force-run start.bat via cmd.exe (fixes broken .bat file association: ftype batfile="%1" %*)
Option Explicit
Dim sh, root, cmd
Set sh = CreateObject("WScript.Shell")
root = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
cmd = "cmd.exe /c cd /d """ & root & """ && call start.bat"
sh.Run cmd, 1, False
