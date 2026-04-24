' IDS Notifier - Launcher (invisible)
' Connexion directe a PostgreSQL sur 192.168.1.2
' Avec notification email aux administrateurs
Set oWS = WScript.CreateObject("WScript.Shell")
sFile = "C:\\Users\\ADM\\Desktop\\NetWeb\\Backend\\notifier.py"
sCmd = "pythonw """ & sFile & """ --db --interval 5 --sound"
oWS.Run sCmd, 0, False
WScript.Sleep 2000
