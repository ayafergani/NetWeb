@echo off
:: ============================================================
:: install_notifier.bat - Installateur complet du notifier IDS
:: Version configurée pour DB sur 192.168.1.2 (utilisateur: aya)
:: ============================================================

setlocal enabledelayedexpansion

:: Couleurs pour la console
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "BLUE=[94m"
set "RESET=[0m"

title IDS Notifier Installer - DB: 192.168.1.2

echo.
echo %BLUE%================================================================%RESET%
echo %BLUE%    🛡️  IDS Alert Notifier - Installation Windows v2.0%RESET%
echo %BLUE%    📡  Base de donnees: 192.168.1.2:5432 (utilisateur: aya)%RESET%
echo %BLUE%================================================================%RESET%
echo.

:: ── 1. Vérifier les droits administrateur ──────────────────────────────────
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%[ERREUR]%RESET% Ce script doit etre execute en tant qu'Administrateur
    echo.
    echo Cliquez droit sur le fichier ^> "Executer en tant qu'administrateur"
    pause
    exit /b 1
)

:: ── 2. Définir les chemins ─────────────────────────────────────────────────
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "NOTIFIER=%SCRIPT_DIR%\notifier.py"
set "RUN_VBS=%SCRIPT_DIR%\run_notifier.vbs"
set "STOP_VBS=%SCRIPT_DIR%\stop_notifier.vbs"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "TASKSCHED=%WINDIR%\System32\taskschd.msc"

:: ── 3. Menu principal ──────────────────────────────────────────────────────
:menu
echo.
echo %BLUE>% Que souhaitez-vous faire ?
echo.
echo    [1] Installer/Reinstaller le notifier
echo    [2] Desinstaller le notifier
echo    [3] Tester les notifications
echo    [4] Tester la connexion a la base de donnees
echo    [5] Verifier l'etat du notifier
echo    [6] Afficher les logs
echo    [7] Ouvrir le dossier de configuration
echo    [8] Quitter
echo.
set /p choice="Votre choix (1-8): "

if "%choice%"=="1" goto install
if "%choice%"=="2" goto uninstall
if "%choice%"=="3" goto test
if "%choice%"=="4" goto test_db
if "%choice%"=="5" goto status
if "%choice%"=="6" goto logs
if "%choice%"=="7" goto config
if "%choice%"=="8" goto end
echo %RED%Choix invalide%RESET%
goto menu

:: ── 4. Test de connexion à la base de données ──────────────────────────────
:test_db
echo.
echo %BLUE%[TEST CONNEXION BASE DE DONNEES]%RESET%
echo.
echo 📡 Hôte: 192.168.1.2
echo 📚 Base: ids_db
echo 👤 User: aya
echo 🔌 Port: 5432
echo.

:: Créer un script Python de test
set "TEST_DB_SCRIPT=%TEMP%\test_db_connection.py"
(
echo import psycopg2
echo import sys
echo.
echo try:
echo     conn = psycopg2.connect(
echo         dbname="ids_db",
echo         user="aya",
echo         password="aya",
echo         host="192.168.1.2",
echo         port="5432",
echo         connect_timeout=5
echo     )
echo     print("✅ Connexion reussie a la base de donnees")
echo    
echo     cur = conn.cursor()
echo     cur.execute("SELECT COUNT(*) FROM alertes")
echo     count = cur.fetchone()[0]
echo     print(f"📊 Nombre d'alertes dans la base: {count}")
echo    
echo     cur.execute("""
echo         SELECT id, attack_type, severity, timestamp
echo         FROM alertes
echo         ORDER BY timestamp DESC
echo         LIMIT 5
echo     """)
echo     print("\n📋 5 dernieres alertes:")
echo     for row in cur.fetchall():
echo         print(f"   - [{row[2]}] {row[1]} ({row[3]})")
echo    
echo     conn.close()
echo     sys.exit(0)
echo except psycopg2.OperationalError as e:
echo     print(f"❌ Erreur de connexion: {e}")
echo     print("\n💡 Verifications:")
echo     print("   1. PostgreSQL est-il installe sur 192.168.1.2 ?")
echo     print("   2. Le service PostgreSQL est-il demarre ?")
echo     print("   3. Le fichier pg_hba.conf autorise-t-il les connexions ?")
echo     print("   4. Le firewall autorise-t-il le port 5432 ?")
echo     sys.exit(1)
echo except Exception as e:
echo     print(f"❌ Erreur inattendue: {e}")
echo     sys.exit(1)
) > "%TEST_DB_SCRIPT%"

python "%TEST_DB_SCRIPT%"
del "%TEST_DB_SCRIPT%" 2>nul

echo.
pause
goto menu

:: ── 5. Installation ────────────────────────────────────────────────────────
:install
echo.
echo %GREEN%[1/9]%RESET% Verification de l'environnement Python...

:: Vérifier Python
where python >nul 2>&1
if errorlevel 1 (
    echo %RED%[ERREUR]%RESET% Python non trouve dans le PATH
    echo.
    echo Téléchargez Python depuis: https://www.python.org/downloads/
    echo N'OUBLIEZ PAS de cocher "Add Python to PATH" lors de l'installation
    pause
    goto menu
)

python --version >nul 2>&1
if errorlevel 1 (
    echo %RED%[ERREUR]%RESET% Python ne repond pas correctement
    pause
    goto menu
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set "PY_VERSION=%%i"
echo %GREEN%✓%RESET% Python %PY_VERSION% trouve

:: Vérifier pip
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo %RED%[ERREUR]%RESET% Pip non trouve, installation...
    python -m ensurepip --upgrade
)

:: ── 6. Test de connexion à la DB avant installation ────────────────────────
echo.
echo %GREEN%[2/9]%RESET% Test de connexion a la base de donnees...

:: Créer un script de test rapide
set "TEST_SCRIPT=%TEMP%\test_db.py"
(
echo import psycopg2
echo try:
echo     conn = psycopg2.connect(
echo         dbname="ids_db",
echo         user="aya",
echo         password="aya",
echo         host="192.168.1.2",
echo         port="5432",
echo         connect_timeout=3
echo     )
echo     conn.close()
echo     print("OK")
echo except:
echo     print("FAIL")
) > "%TEST_SCRIPT%"

for /f "delims=" %%i in ('python "%TEST_SCRIPT%" 2^>nul') do set "DB_TEST=%%i"
del "%TEST_SCRIPT%" 2>nul

if "%DB_TEST%"=="OK" (
    echo %GREEN%✓%RESET% Connexion a la base de donnees reussie
) else (
    echo %YELLOW%⚠%RESET% Attention: Impossible de se connecter a la base de donnees
    echo.
    echo    Verifiez que PostgreSQL est accessible sur 192.168.1.2:5432
    echo    Le notifier demarrera quand meme mais ne pourra pas recuperer les alertes
    echo.
    set /p continue="Continuer quand meme (O/N) ? "
    if /i not "!continue!"=="O" goto menu
)

:: ── 7. Installation des dépendances ─────────────────────────────────────────
echo.
echo %GREEN%[3/9]%RESET% Installation des dependances Python...
echo.

:: Mettre à jour pip
python -m pip install --upgrade pip --quiet

:: Installer les dépendances
echo Installation de psycopg2-binary (connexion PostgreSQL)...
python -m pip install --quiet psycopg2-binary

echo Installation de requests...
python -m pip install --quiet requests

echo Installation de plyer...
python -m pip install --quiet plyer

echo Installation de winotify...
python -m pip install --quiet winotify

echo Installation de win10toast-persist...
python -m pip install --quiet win10toast-persist

echo Installation de winrt (notifications avancees)...
python -m pip install --quiet winrt

echo %GREEN%✓%RESET% Toutes les dependances sont installees

:: ── 8. Création des scripts VBS ────────────────────────────────────────────
echo.
echo %GREEN%[4/9]%RESET% Creation des scripts de lancement...

:: Script de démarrage (mode DB directe)
(
    echo ' IDS Notifier - Launcher (invisible^)
    echo ' Connexion directe a PostgreSQL sur 192.168.1.2
    echo Set oWS = WScript.CreateObject^("WScript.Shell"^)
    echo sFile = "%NOTIFIER:\=\\%"
    echo sCmd = "pythonw """ ^& sFile ^& """ --db --interval 5 --sound"
    echo oWS.Run sCmd, 0, False
    echo WScript.Sleep 2000
) > "%RUN_VBS%"

:: Script d'arrêt
(
    echo ' IDS Notifier - Stopper le processus
    echo Set oWS = WScript.CreateObject^("WScript.Shell"^)
    echo oWS.Run "taskkill /F /IM pythonw.exe", 0, False
    echo WScript.Sleep 1000
) > "%STOP_VBS%"

echo %GREEN%✓%RESET% Scripts crees

:: ── 9. Ajout au démarrage ───────────────────────────────────────────────────
echo.
echo %GREEN%[5/9]%RESET% Ajout au demarrage Windows...

:: Supprimer l'ancienne installation si existante
if exist "%STARTUP%\IDS_Notifier.vbs" del /Q "%STARTUP%\IDS_Notifier.vbs"
if exist "%STARTUP%\IDS_Notifier.lnk" del /Q "%STARTUP%\IDS_Notifier.lnk"

:: Copier le nouveau script
copy /Y "%RUN_VBS%" "%STARTUP%\IDS_Notifier.vbs" >nul
echo %GREEN%✓%RESET% Ajoute au dossier Demarrage

:: ── 10. Ajout au Planificateur de tâches (redémarrage plus fiable) ──────────
echo.
echo %GREEN%[6/9]%RESET% Creation d'une tache planifiee (plus fiable)...

:: Supprimer l'ancienne tâche
schtasks /delete /tn "IDS_Notifier" /f >nul 2>&1

:: Créer la nouvelle tâche
schtasks /create /tn "IDS_Notifier" /tr "wscript.exe \"%RUN_VBS%\"" /sc onstart /delay 0001:00 /ru "SYSTEM" /f >nul 2>&1
if %errorlevel% equ 0 (
    echo %GREEN%✓%RESET% Tache planifiee creee (demarrage au boot)
) else (
    echo %YELLOW%⚠%RESET% Impossible de creer la tache planifiee
    echo    Le notifier demarrera via le dossier Demarrage uniquement
)

:: ── 11. Fichier de configuration ─────────────────────────────────────────────
echo.
echo %GREEN%[7/9]%RESET% Configuration de la base de donnees...

set "CONFIG_DIR=%APPDATA%\IDS_Notifier"
if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"

:: Créer un fichier de configuration avec vos paramètres
(
    echo # IDS Notifier Configuration
    echo # Base de donnees PostgreSQL
    echo DB_NAME=ids_db
    echo DB_USER=aya
    echo DB_PASSWORD=aya
    echo DB_HOST=192.168.1.2
    echo DB_PORT=5432
    echo.
    echo # Options
    echo POLL_INTERVAL=5
    echo ENABLE_SOUND=true
    echo MODE=db_direct
) > "%CONFIG_DIR%\notifier.conf"

:: Créer aussi un fichier .env pour faciliter les modifications
(
    echo DB_NAME=ids_db
    echo DB_USER=aya
    echo DB_PASSWORD=aya
    echo DB_HOST=192.168.1.2
    echo DB_PORT=5432
) > "%CONFIG_DIR%\.env"

echo %GREEN%✓%RESET% Configuration creee dans %CONFIG_DIR%
echo    📁 Base: 192.168.1.2:5432/ids_db (user: aya)

:: ── 12. Créer un raccourci sur le bureau ────────────────────────────────────
echo.
echo %GREEN%[8/9]%RESET% Creation des raccourcis...

set "DESKTOP=%USERPROFILE%\Desktop"
set "SHORTCUT=%DESKTOP%\IDS_Notifier.lnk"

:: Créer un script PowerShell pour le raccourci
powershell -Command "$WS = New-Object -ComObject WScript.Shell; $SC = $WS.CreateShortcut('%SHORTCUT%'); $SC.TargetPath = 'wscript.exe'; $SC.Arguments = '\"%RUN_VBS%\"'; $SC.Description = 'IDS Alert Notifier - DB: 192.168.1.2'; $SC.Save()" 2>nul
if exist "%SHORTCUT%" (
    echo %GREEN%✓%RESET% Raccourci cree sur le bureau
)

:: ── 13. Démarrer immédiatement ─────────────────────────────────────────────
echo.
echo %GREEN%[9/9]%RESET% Demarrage immediat du notifier...

:: Arrêter les instances existantes
taskkill /F /IM pythonw.exe >nul 2>&1
timeout /t 2 /nobreak >nul

:: Démarrer
wscript "%RUN_VBS%"

:: Vérifier que ça a démarré
timeout /t 3 /nobreak >nul
tasklist /FI "IMAGENAME eq pythonw.exe" 2>nul | find /I "pythonw.exe" >nul
if %errorlevel% equ 0 (
    echo %GREEN%✓%RESET% Notifier demarre avec succes en arriere-plan
    echo    📡 Surveillance de la base: 192.168.1.2/ids_db
) else (
    echo %RED%✗%RESET% Erreur: Le notifier n'a pas demarre
    echo    Verifiez les logs: %CONFIG_DIR%\notifier.log
)

:: ── 14. Tester une notification ────────────────────────────────────────────
echo.
echo %YELLOW%Test de notification...%RESET%
timeout /t 2 /nobreak >nul

:: Créer un script de test temporaire
set "TEST_SCRIPT=%TEMP%\test_notify.vbs"
(
    echo Set oWS = WScript.CreateObject^("WScript.Shell"^)
    echo oWS.Popup "IDS Notifier est operationnel !" ^& vbCrLf ^& vbCrLf ^& "Surveillance de la base:" ^& vbCrLf ^& "192.168.1.2/ids_db (user: aya)" ^& vbCrLf ^& vbCrLf ^& "Vous recevrez des notifications pour chaque alerte.", 8, "IDS Monitor - Test DB", 64
) > "%TEST_SCRIPT%"
wscript "%TEST_SCRIPT%"
del "%TEST_SCRIPT%" 2>nul

:: ── 15. Résumé final ───────────────────────────────────────────────────────
echo.
echo %GREEN%================================================================%RESET%
echo %GREEN%              ✅ INSTALLATION REUSSIE ✅%RESET%
echo %GREEN%================================================================%RESET%
echo.
echo 📡 Configuration base de donnees:
echo    └─ Hôte....: 192.168.1.2:5432
echo    └─ Base....: ids_db
echo    └─ User....: aya
echo.
echo 📍 Le notifier tourne en arriere-plan
echo 📍 Il demarrera automatiquement a chaque session Windows
echo 📍 Mode: Connexion directe PostgreSQL (sans Flask)
echo.
echo 📁 Logs....: %CONFIG_DIR%\notifier.log
echo 📁 Config..: %CONFIG_DIR%\notifier.conf
echo.
echo %BLUE>% Pour arreter le notifier:
echo    - Gestionnaire des taches ^> Arreter "pythonw.exe"
echo    - Ou double-cliquez sur: "%STOP_VBS%"
echo.
echo %BLUE>% Pour tester:
echo    - Ajoutez une alerte dans la base de donnees
echo    - Le notifier affichera une notification Windows automatiquement
echo.
echo %YELLOW>% Note: Si la base 192.168.1.2 n'est pas accessible,
echo    le notifier attendra et reconnectera automatiquement.
echo.
pause
goto menu

:: ── 16. Désinstallation ────────────────────────────────────────────────────
:uninstall
echo.
echo %RED%[DESINSTALLATION]%RESET%
echo.
set /p confirm="Confirmez la desinstallation (O/N) ? "
if /i not "%confirm%"=="O" goto menu

echo %YELLOW%▸%RESET% Arret du notifier...
taskkill /F /IM pythonw.exe >nul 2>&1

echo %YELLOW%▸%RESET% Suppression du dossier Demarrage...
if exist "%STARTUP%\IDS_Notifier.vbs" del /Q "%STARTUP%\IDS_Notifier.vbs"

echo %YELLOW%▸%RESET% Suppression de la tache planifiee...
schtasks /delete /tn "IDS_Notifier" /f >nul 2>&1

echo %YELLOW%▸%RESET% Suppression des scripts...
if exist "%RUN_VBS%" del /Q "%RUN_VBS%"
if exist "%STOP_VBS%" del /Q "%STOP_VBS%"

echo %YELLOW%▸%RESET% Suppression du raccourci bureau...
set "DESKTOP=%USERPROFILE%\Desktop"
if exist "%DESKTOP%\IDS_Notifier.lnk" del /Q "%DESKTOP%\IDS_Notifier.lnk"

echo %YELLOW%▸%RESET% Suppression des fichiers de configuration...
set "CONFIG_DIR=%APPDATA%\IDS_Notifier"
if exist "%CONFIG_DIR%" rmdir /S /Q "%CONFIG_DIR%"

echo.
echo %GREEN%✓%RESET% Desinstallation terminee
echo.
pause
goto menu

:: ── 17. Test de notification ───────────────────────────────────────────────
:test
echo.
echo %BLUE%[TEST NOTIFICATION]%RESET%
echo.

:: Créer une alerte de test directement dans la base
set "TEST_ALERT=%TEMP%\test_alert.py"
(
echo import psycopg2
echo from datetime import datetime
echo import json
echo.
echo try:
echo     conn = psycopg2.connect(
echo         dbname="ids_db",
echo         user="aya",
echo         password="aya",
echo         host="192.168.1.2",
echo         port="5432"
echo     )
echo     cur = conn.cursor()
echo    
echo     # Insertion d'une alerte de test
echo     cur.execute("""
echo         INSERT INTO alertes (attack_type, source_ip, destination_ip, severity, protocol, timestamp, details)
echo         VALUES (%%s, %%s, %%s, %%s, %%s, NOW(), %%s)
echo         RETURNING id
echo     """, (
echo         "Test Notification",
echo         "192.168.1.100",
echo         "192.168.1.200",
echo         "medium",
echo         "TCP",
echo         json.dumps({"test": "Notification de test"})
echo     ))
echo    
echo     alert_id = cur.fetchone()[0]
echo     conn.commit()
echo     print(f"✅ Alerte de test creee (ID: {alert_id})")
echo     print("📨 Une notification Windows devrait apparaitre dans 5 secondes")
echo    
echo     conn.close()
echo except Exception as e:
echo     print(f"❌ Erreur: {e}")
echo     print("Verifiez que la base de donnees est accessible")
) > "%TEST_ALERT%"

python "%TEST_ALERT%"
del "%TEST_ALERT%" 2>nul

echo.
echo %GREEN%✓%RESET% Test termine
pause
goto menu

:: ── 18. État du notifier ───────────────────────────────────────────────────
:status
echo.
echo %BLUE%[ETAT DU NOTIFIER]%RESET%
echo.

:: Vérifier si le processus tourne
tasklist /FI "IMAGENAME eq pythonw.exe" 2>nul | find /I "pythonw.exe" >nul
if %errorlevel% equ 0 (
    echo %GREEN%✓%RESET% Notifier actif ^(pythonw.exe en cours^)
    echo.
    echo 📡 Surveillance: 192.168.1.2:5432/ids_db (user: aya)
    echo.
   
    :: Afficher les dernières lignes du log
    set "CONFIG_DIR=%APPDATA%\IDS_Notifier"
    if exist "%CONFIG_DIR%\notifier.log" (
        echo Dernieres activites:
        echo %YELLOW%------------------------------------------------%RESET%
        powershell -Command "Get-Content '%CONFIG_DIR%\notifier.log' -Tail 8"
        echo %YELLOW%------------------------------------------------%RESET%
    )
) else (
    echo %RED%✗%RESET% Notifier INACTIF
    echo.
    echo Pour demarrer le notifier:
    echo   - Double-cliquez sur: "%RUN_VBS%"
    echo   - Ou redemarrez Windows
)
echo.
pause
goto menu

:: ── 19. Logs ──────────────────────────────────────────────────────────────
:logs
echo.
echo %BLUE%[LOGS]%RESET%
set "CONFIG_DIR=%APPDATA%\IDS_Notifier"
if exist "%CONFIG_DIR%\notifier.log" (
    echo.
    echo Dernieres 20 lignes des logs:
    echo %YELLOW%------------------------------------------------%RESET%
    powershell -Command "Get-Content '%CONFIG_DIR%\notifier.log' -Tail 20"
    echo %YELLOW%------------------------------------------------%RESET%
    echo.
    echo Options:
    echo    [O] Ouvrir le fichier complet
    echo    [C] Effacer les logs
    echo    [R] Retour
    echo.
    set /p log_choice="Choix (O/C/R) : "
    if /i "!log_choice!"=="O" notepad "%CONFIG_DIR%\notifier.log"
    if /i "!log_choice!"=="C" (
        echo. > "%CONFIG_DIR%\notifier.log"
        echo %GREEN%Logs effaces%RESET%
    )
) else (
    echo %YELLOW%Aucun fichier de logs trouve%RESET%
    echo    Le notifier n'a peut-etre jamais ete lance
)
pause
goto menu

:: ── 20. Configuration ──────────────────────────────────────────────────────
:config
echo.
echo %BLUE%[CONFIGURATION]%RESET%
set "CONFIG_DIR=%APPDATA%\IDS_Notifier"
if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"
explorer "%CONFIG_DIR%"
echo %GREEN%Dossier de configuration ouvert%RESET%
echo.
echo %YELLOW>% Pour modifier les parametres de connexion:
echo    Editez le fichier ".env" dans ce dossier
pause
goto menu

:: ── 21. Fin ─────────────────────────────────────────────────────────────────
:end
echo.
echo %BLUE%Merci d'avoir utilise IDS Notifier!%RESET%
echo.
exit /b 0