Set WshShell = CreateObject("WScript.Shell")
scriptPath = WshShell.CurrentDirectory & "\sanctum-suite-gui-launcher.ps1"
If InStr(scriptPath, "\") = 0 Then
    scriptPath = WshShell.CurrentDirectory & "\sanctum-suite-gui-launcher.ps1"
End If
WshShell.Run "powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File """ & scriptPath & """", 0, False
