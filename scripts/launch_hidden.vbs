' Launches python.exe -m <module> with no console window.
' Usage:  wscript.exe launch_hidden.vbs <module.path>
'
' We use python.exe rather than pythonw.exe because some bundled native
' code (mediapipe / TF Lite / cv2) interacts badly with pythonw's null
' stdio handles during tracking-mode startup. The console is hidden via
' WshShell.Run windowStyle = 0, so it never flashes on screen.

Option Explicit

If WScript.Arguments.Count < 1 Then
    WScript.Echo "usage: launch_hidden.vbs <python.module.path>"
    WScript.Quit 2
End If

Dim moduleName, fso, scriptDir, projectRoot, pythonExe, shell, cmd

moduleName = WScript.Arguments.Item(0)

Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir   = fso.GetParentFolderName(WScript.ScriptFullName)        ' ...\scripts
projectRoot = fso.GetParentFolderName(scriptDir)                     ' ...\EyeCursor
pythonExe   = projectRoot & "\venv\Scripts\python.exe"

If Not fso.FileExists(pythonExe) Then
    WScript.Echo "Missing " & pythonExe & vbCrLf & _
                 "Run setup_windows.bat first."
    WScript.Quit 1
End If

Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = projectRoot
cmd = """" & pythonExe & """ -m " & moduleName

' 0 = hidden window, False = don't wait. Detaches so wscript exits immediately.
shell.Run cmd, 0, False
