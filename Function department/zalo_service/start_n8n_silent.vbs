Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd.exe /c """ & CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & "\start_n8n.bat""", 0, False
