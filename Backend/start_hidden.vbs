' Snort IDS - Lancement automatique du backend API
Set oWS = WScript.CreateObject("WScript.Shell")

' Lancer logrotation.py (backend API)
sFile = "C:\Users\HP\Downloads\NetWeb\Backend\logrotation.py"
sCmd = "python """ & sFile & """"
oWS.Run sCmd, 0, False

' Petite pause pour éviter les conflits
WScript.Sleep 2000