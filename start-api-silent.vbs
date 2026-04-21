' start-api-silent.vbs — launch start-api.bat with no visible console window.
' Used by the auto-start scheduled task so the server runs in the background.
Set wsh = CreateObject("WScript.Shell")
wsh.Run """" & CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & "\start-api.bat""", 0, False
