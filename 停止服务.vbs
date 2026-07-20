Option Explicit
Dim sh, root, cmd
Set sh = CreateObject("WScript.Shell")
root = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
cmd = "cmd.exe /c cd /d """ & root & """ && call stop.bat"
sh.Run cmd, 1, False
