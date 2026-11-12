Set shell = CreateObject("WScript.Shell")
cmdPath = shell.ExpandEnvironmentStrings("%COMSPEC%")
scriptDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
launcher = scriptDir & "\start-sanctum-suite.cmd"

shell.Run """" & cmdPath & """ /c """" & launcher & """"", 0, False
