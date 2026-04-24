@echo off
:: ============================================================
:: install_notifier.bat - Installateur complet du notifier IDS
:: Version configurée pour DB sur 192.168.1.2 (utilisateur: aya)
:: Avec notification email aux administrateurs
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
echo %BLUE%    📧  Notification email aux administrateurs incluse%RESET%
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
echo %BLUE% Que souhaitez-vous faire ?
echo.
echo    [1] Installer/Reinstaller le notifier
echo    [2] Desinstaller le notifier
echo    [3] Tester les notifications (Windows + Email)
echo    [4] Tester la connexion a la base de donnees
echo    [5] Verifier l'etat du notifier
echo    [6] Afficher les logs
echo    [7] Ouvrir le dossier de configuration
echo    [8] Configurer les emails (administrateurs)
echo    [9] Tester l'envoi d'email uniquement
echo    [10] Quitter
echo.
set /p choice="Votre choix (1-10): "

if "%choice%"=="1" goto install
if "%choice%"=="2" goto uninstall
if "%choice%"=="3" goto test
if "%choice%"=="4" goto test_db
if "%choice%"=="5" goto status
if "%choice%"=="6" goto logs
if "%choice%"=="7" goto config
if "%choice%"=="8" goto config_email
if "%choice%"=="9" goto test_email
if "%choice%"=="10" goto end
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
echo     # Vérifier les administrateurs
echo     cur.execute("SELECT username, email FROM utilisateur WHERE role = 'admin' AND email IS NOT NULL AND email != ''")
echo     admins = cur.fetchall()
echo     if admins:
echo         print(f"\n👥 Administrateurs trouves dans la base: {len(admins)}")
echo         for username, email in admins:
echo             print(f"   ✅ {username}: {email}")
echo     else:
echo         print("\n⚠️ AUCUN administrateur avec email trouve dans la table utilisateur")
echo         print("   Pour recevoir des emails, ajoutez des utilisateurs avec role='admin' et un email valide")
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

:: ── 5. Configuration email ─────────────────────────────────────────────────
:config_email
echo.
echo %BLUE%[CONFIGURATION EMAIL]%RESET%
echo.
echo Cette configuration permet d'envoyer des notifications email
echo aux administrateurs lors des alertes IDS.
echo.
echo %YELLOW>% Les emails seront envoyes aux utilisateurs ayant:
echo    - role = 'admin' dans la table 'utilisateur'
echo    - un email valide renseigne
echo.

set "CONFIG_DIR=%APPDATA%\IDS_Notifier"
if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"
set "EMAIL_CONFIG=%CONFIG_DIR%\email_config.json"

if exist "%EMAIL_CONFIG%" (
    echo %GREEN%✓%RESET% Fichier de configuration email existant
    echo.
    type "%EMAIL_CONFIG%"
    echo.
    echo Souhaitez-vous le modifier ?
    echo    [1] Modifier la configuration
    echo    [2] Supprimer la configuration
    echo    [3] Retour
    echo.
    set /p email_choice="Choix (1-3): "
    if "!email_choice!"=="1" goto edit_email_config
    if "!email_choice!"=="2" (
        del /Q "%EMAIL_CONFIG%" 2>nul
        echo %GREEN%Configuration email supprimee%RESET%
        pause
        goto menu
    )
    if "!email_choice!"=="3" goto menu
)

:edit_email_config
echo.
echo %YELLOW%Configuration SMTP%RESET%
echo.
echo Exemples de serveurs SMTP:
echo    📧 Gmail:      smtp.gmail.com:587
echo    📧 Outlook:    smtp-mail.outlook.com:587
echo    📧 Yahoo:      smtp.mail.yahoo.com:587
echo    📧 Orange:     smtp.orange.fr:465
echo    📧 SFR:        smtp.sfr.fr:465
echo    📧 Pro/Entreprise: smtp.votredomaine.com
echo.
echo %YELLOW%⚠️  Pour Gmail, utilisez un "Mot de passe d'application" (2FA active)%RESET%
echo.
set /p smtp_server="Serveur SMTP (ex: smtp.gmail.com): "
set /p smtp_port="Port SMTP (587 pour TLS, 465 pour SSL): "
set /p smtp_user="Email expediteur: "
set /p smtp_password="Mot de passe / Cle d'application: "
set /p from_name="Nom affiche (ex: IDS Monitoring): "
if "!from_name!"=="" set "from_name=IDS Monitoring System"

:: Créer le fichier de configuration
(
echo {
echo     "smtp_server": "!smtp_server!",
echo     "smtp_port": !smtp_port!,
echo     "smtp_user": "!smtp_user!",
echo     "smtp_password": "!smtp_password!",
echo     "use_tls": true,
echo     "from_email": "!smtp_user!",
echo     "from_name": "!from_name!"
echo }
) > "%EMAIL_CONFIG%"

echo.
echo %GREEN%✓%RESET% Configuration email sauvegardee dans %EMAIL_CONFIG%
echo.
echo %YELLOW%⚠️  Securite: Le mot de passe est stocke en clair dans ce fichier%RESET%
echo %YELLOW%   Protegez l'acces a ce dossier.%RESET%
echo.

:: Tester la configuration
echo Voulez-vous tester l'envoi d'email maintenant ?
set /p test_now="Tester (O/N) ? "
if /i "!test_now!"=="O" goto test_email

pause
goto menu

:: ── 6. Test d'envoi d'email ────────────────────────────────────────────────
:test_email
echo.
echo %BLUE%[TEST ENVOI EMAIL]%RESET%
echo.

:: Vérifier la base pour les admins
set "TEST_EMAIL_SCRIPT=%TEMP%\test_email.py"
(
echo import psycopg2
echo import json
echo import smtplib
echo from email.mime.text import MIMEText
echo from email.mime.multipart import MIMEMultipart
echo from pathlib import Path
echo import os
echo import sys
echo.
echo CONFIG_DIR = Path(os.getenv("APPDATA")) / "IDS_Notifier"
echo EMAIL_CONFIG_FILE = CONFIG_DIR / "email_config.json"
echo.
echo # Charger config email
echo email_config = {}
echo if EMAIL_CONFIG_FILE.exists():
echo     with open(EMAIL_CONFIG_FILE, 'r') as f:
echo         email_config = json.load(f)
echo else:
echo     print("❌ Aucune configuration email trouvee")
echo     print("   Lancez d'abord l'option 8 pour configurer les emails")
echo     sys.exit(1)
echo.
echo # Recuperer les admins
echo try:
echo     conn = psycopg2.connect(
echo         dbname="ids_db",
echo         user="aya",
echo         password="aya",
echo         host="192.168.1.2",
echo         port="5432"
echo     )
echo     cur = conn.cursor()
echo     cur.execute("SELECT email, username FROM utilisateur WHERE role = 'admin' AND email IS NOT NULL AND email != ''")
echo     admins = cur.fetchall()
echo     conn.close()
echo except Exception as e:
echo     print(f"❌ Erreur connexion DB: {e}")
echo     sys.exit(1)
echo.
echo if not admins:
echo     print("⚠️ Aucun administrateur avec email trouve dans la table utilisateur")
echo     print("")
echo     print("Pour ajouter un administrateur, executez dans PostgreSQL:")
echo     print("  INSERT INTO utilisateur (username, email, role) VALUES ('admin', 'email@exemple.com', 'admin');")
echo     sys.exit(1)
echo.
echo print(f"📧 {len(admins)} administrateur(s) trouve(s):")
echo for email, username in admins:
echo     print(f"   ✅ {username}: {email}")
echo.
echo # Envoyer email de test
echo test_sent = False
echo for email, username in admins:
echo     try:
echo         msg = MIMEMultipart('alternative')
echo         msg['From'] = f"{email_config.get('from_name', 'IDS Monitor')} <{email_config['from_email']}>"
echo         msg['To'] = email
echo         msg['Subject'] = "[TEST] IDS Notifier - Test de notification"
echo.
echo         text_body = f"""
echo Test du systeme de notification IDS
echo =====================================
echo.
echo Ceci est un email de test envoye depuis votre systeme IDS Notifier.
echo.
echo ✅ La configuration email fonctionne correctement.
echo.
echo Vous recevrez des notifications email pour chaque alerte IDS.
echo.
echo ---
echo Heure du test: {__import__('datetime').datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
echo """
echo.
echo         html_body = f"""
echo ^<!DOCTYPE html^>
echo ^<html^>
echo ^<head^>^<style^>
echo     body { font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f4; }
echo     .container { max-width: 600px; margin: 20px auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
echo     .header { background-color: #4CAF50; color: white; padding: 20px; text-align: center; }
echo     .header h2 { margin: 0; }
echo     .content { padding: 20px; }
echo     .success { color: #4CAF50; font-weight: bold; font-size: 18px; }
echo     .info { background-color: #e8f5e9; padding: 15px; border-radius: 5px; margin: 15px 0; }
echo     .footer { background-color: #f1f1f1; padding: 10px; text-align: center; font-size: 12px; color: #666; }
echo ^</style^>^</head^>
echo ^<body^>
echo     ^<div class="container"^>
echo         ^<div class="header"^>
echo             ^<h2^>🛡️ IDS Notifier - Test de notification^</h2^>
echo         ^</div^>
echo         ^<div class="content"^>
echo             ^<p class="success"^>✅ Test reussi !^</p^>
echo             ^<p^>Ceci est un email de test depuis votre systeme IDS Notifier.^</p^>
echo             ^<div class="info"^>
echo                 ^<strong^>Configuration SMTP :^</strong^><br^>
echo                 Serveur: {email_config.get('smtp_server')}<br^>
echo                 Port: {email_config.get('smtp_port')}<br^>
echo                 Expediteur: {email_config.get('from_email')}
echo             ^</div^>
echo             ^<p^>Vous recevrez des notifications email pour chaque alerte IDS.^</p^>
echo             ^<hr^>
echo             ^<p^>^<small^>Heure du test: {__import__('datetime').datetime.now().strftime('%d/%m/%Y %H:%M:%S')}^</small^>^</p^>
echo         ^</div^>
echo         ^<div class="footer"^>
echo             IDS Notifier - Système de détection d'intrusion
echo         ^</div^>
echo     ^</div^>
echo ^</body^>
echo ^</html^>
echo """
echo.
echo         msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
echo         msg.attach(MIMEText(html_body, 'html', 'utf-8'))
echo.
echo         if email_config.get('use_tls', True):
echo             server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
echo             server.starttls()
echo         else:
echo             server = smtplib.SMTP_SSL(email_config['smtp_server'], email_config['smtp_port'])
echo.
echo         server.login(email_config['smtp_user'], email_config['smtp_password'])
echo         server.send_message(msg)
echo         server.quit()
echo.
echo         print(f"✅ Email de test envoye a {username} ({email})")
echo         test_sent = True
echo     except Exception as e:
echo         print(f"❌ Erreur envoi a {email}: {e}")
echo.
echo if test_sent:
echo     print("\n✅ Test termine avec succes")
echo else:
echo     print("\n❌ Aucun email n'a pu etre envoye")
echo     sys.exit(1)
) > "%TEST_EMAIL_SCRIPT%"

python "%TEST_EMAIL_SCRIPT%"
del "%TEST_EMAIL_SCRIPT%" 2>nul

echo.
pause
goto menu

:: ── 7. Installation ────────────────────────────────────────────────────────
:install
echo.
echo %GREEN%[1/11]%RESET% Verification de l'environnement Python...

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

:: ── 8. Test de connexion à la DB avant installation ────────────────────────
echo.
echo %GREEN%[2/11]%RESET% Test de connexion a la base de donnees...

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

:: ── 9. Installation des dépendances ─────────────────────────────────────────
echo.
echo %GREEN%[3/11]%RESET% Installation des dependances Python...
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

:: ── 10. Création des scripts VBS ───────────────────────────────────────────
echo.
echo %GREEN%[4/11]%RESET% Creation des scripts de lancement...

:: Script de démarrage (mode DB directe)
(
    echo ' IDS Notifier - Launcher (invisible^)
    echo ' Connexion directe a PostgreSQL sur 192.168.1.2
    echo ' Avec notification email aux administrateurs
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

:: ── 11. Ajout au démarrage ─────────────────────────────────────────────────
echo.
echo %GREEN%[5/11]%RESET% Ajout au demarrage Windows...

:: Supprimer l'ancienne installation si existante
if exist "%STARTUP%\IDS_Notifier.vbs" del /Q "%STARTUP%\IDS_Notifier.vbs"
if exist "%STARTUP%\IDS_Notifier.lnk" del /Q "%STARTUP%\IDS_Notifier.lnk"

:: Copier le nouveau script
copy /Y "%RUN_VBS%" "%STARTUP%\IDS_Notifier.vbs" >nul
echo %GREEN%✓%RESET% Ajoute au dossier Demarrage

:: ── 12. Ajout au Planificateur de tâches ───────────────────────────────────
echo.
echo %GREEN%[6/11]%RESET% Creation d'une tache planifiee (plus fiable)...

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

:: ── 13. Fichier de configuration ───────────────────────────────────────────
echo.
echo %GREEN%[7/11]%RESET% Configuration de la base de donnees...

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

:: ── 14. Configurer le fichier email par défaut ─────────────────────────────
echo.
echo %GREEN%[8/11]%RESET% Configuration email...

set "EMAIL_CONFIG=%CONFIG_DIR%\email_config.json"
if not exist "%EMAIL_CONFIG%" (
    echo %YELLOW%⚠%RESET% Aucune configuration email trouvee
    echo.
    echo Souhaitez-vous configurer l'envoi d'emails maintenant ?
    echo (Les emails seront envoyes aux utilisateurs avec role='admin')
    echo.
    set /p config_email_now="Configurer email (O/N) ? "
    if /i "!config_email_now!"=="O" (
        call :config_email
    ) else (
        echo.
        echo %YELLOW%Vous pourrez configurer les emails plus tard via l'option 8%RESET%
        echo.
    )
) else (
    echo %GREEN%✓%RESET% Configuration email existante
)

:: ── 15. Créer un raccourci sur le bureau ───────────────────────────────────
echo.
echo %GREEN%[9/11]%RESET% Creation des raccourcis...

set "DESKTOP=%USERPROFILE%\Desktop"
set "SHORTCUT=%DESKTOP%\IDS_Notifier.lnk"

:: Créer un script PowerShell pour le raccourci
powershell -Command "$WS = New-Object -ComObject WScript.Shell; $SC = $WS.CreateShortcut('%SHORTCUT%'); $SC.TargetPath = 'wscript.exe'; $SC.Arguments = '\"%RUN_VBS%\"'; $SC.Description = 'IDS Alert Notifier - DB: 192.168.1.2'; $SC.Save()" 2>nul
if exist "%SHORTCUT%" (
    echo %GREEN%✓%RESET% Raccourci cree sur le bureau
)

:: ── 16. Démarrer immédiatement ─────────────────────────────────────────────
echo.
echo %GREEN%[10/11]%RESET% Demarrage immediat du notifier...

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
    echo    📧 Notification email activee pour les administrateurs
) else (
    echo %RED%✗%RESET% Erreur: Le notifier n'a pas demarre
    echo    Verifiez les logs: %CONFIG_DIR%\notifier.log
)

:: ── 17. Tester une notification ───────────────────────────────────────────
echo.
echo %GREEN%[11/11]%RESET% Test de notification...
timeout /t 2 /nobreak >nul

:: Créer une alerte de test dans la base
set "TEST_ALERT=%TEMP%\create_test_alert.py"
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
echo     cur.execute("""
echo         INSERT INTO alertes (attack_type, source_ip, destination_ip, severity, protocol, timestamp, details)
echo         VALUES (%%s, %%s, %%s, %%s, %%s, NOW(), %%s)
echo     """, (
echo         "Test Installation - IDS Activee",
echo         "192.168.1.100",
echo         "192.168.1.200",
echo         "low",
echo         "TCP",
echo         json.dumps({"test": "Notification de test d''installation", "source": "IDS Notifier"})
echo     ))
echo     conn.commit()
echo     print("✅ Alerte de test creee")
echo     conn.close()
echo except Exception as e:
echo     print(f"Note: {e}")
) > "%TEST_ALERT%"

python "%TEST_ALERT%" 2>nul
del "%TEST_ALERT%" 2>nul

:: Créer un message de confirmation visuelle
set "TEST_SCRIPT=%TEMP%\test_notify.vbs"
(
    echo Set oWS = WScript.CreateObject^("WScript.Shell"^)
    echo oWS.Popup "IDS Notifier est operationnel !" ^& vbCrLf ^& vbCrLf ^& "Surveillance de la base:" ^& vbCrLf ^& "192.168.1.2/ids_db (user: aya)" ^& vbCrLf ^& vbCrLf ^& "📧 Notifications email actives" ^& vbCrLf ^& vbCrLf ^& "Une alerte de test a ete creee dans la base." ^& vbCrLf ^& "Une notification Windows et un email seront envoyes sous 5-10 secondes.", 8, "IDS Monitor - Installation terminee", 64
) > "%TEST_SCRIPT%"
wscript "%TEST_SCRIPT%"
del "%TEST_SCRIPT%" 2>nul

:: ── 18. Résumé final ───────────────────────────────────────────────────────
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
echo 📧 Notification email:
if exist "%EMAIL_CONFIG%" (
    echo    └─ ✅ Configuree
    echo    └─ Envoi aux administrateurs de la table 'utilisateur'
) else (
    echo    └─ ⚠️ Non configuree (option 8 du menu)
)
echo.
echo 📍 Le notifier tourne en arriere-plan
echo 📍 Il demarrera automatiquement a chaque session Windows
echo 📍 Mode: Connexion directe PostgreSQL
echo.
echo 📁 Logs....: %CONFIG_DIR%\notifier.log
echo 📁 Config..: %CONFIG_DIR%\notifier.conf
echo 📁 Emails..: %CONFIG_DIR%\email_config.json
echo.
echo %BLUE% Pour arreter le notifier:
echo    - Gestionnaire des taches ^> Arreter "pythonw.exe"
echo    - Ou double-cliquez sur: "%STOP_VBS%"
echo.
echo %BLUE% Pour tester les emails:
echo    - Menu option 9 "Tester l'envoi d'email"
echo.
echo %YELLOW% Note: Pour recevoir des emails, assurez-vous que:
echo    1. La configuration email est faite (option 8)
echo    2. Des administrateurs existent dans la table 'utilisateur':
echo       INSERT INTO utilisateur (username, email, role) VALUES ('admin', 'votre@email.com', 'admin');
echo.
pause
goto menu

:: ── 19. Désinstallation ────────────────────────────────────────────────────
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

:: ── 20. Test de notification (Windows + Email) ─────────────────────────────
:test
echo.
echo %BLUE%[TEST NOTIFICATION]%RESET%
echo.
echo Ce test va creer une alerte dans la base.
echo Une notification Windows sera envoyee.
if exist "%APPDATA%\IDS_Notifier\email_config.json" (
    echo Un email sera aussi envoye aux administrateurs.
) else (
    echo %YELLOW%⚠️ Email non configure - seul Windows sera teste%RESET%
)
echo.

:: Créer une alerte de test directement dans la base
set "TEST_ALERT=%TEMP%\test_alert.py"
(
echo import psycopg2
echo from datetime import datetime
echo import json
echo import sys
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
echo     cur.execute("""
echo         INSERT INTO alertes (attack_type, source_ip, destination_ip, severity, protocol, timestamp, details)
echo         VALUES (%%s, %%s, %%s, %%s, %%s, NOW(), %%s)
echo         RETURNING id
echo     """, (
echo         "Test ALERTE - Simulation d''attaque",
echo         "192.168.1.100",
echo         "192.168.1.200",
echo         "medium",
echo         "TCP",
echo         json.dumps({"test": "Notification de test manuelle", "source": "IDS Notifier", "type": "test"})
echo     ))
echo    
echo     alert_id = cur.fetchone()[0]
echo     conn.commit()
echo     print(f"✅ Alerte de test creee (ID: {alert_id})")
echo     print("📨 Notification Windows envoyee")
echo     if len(sys.argv) > 1 and sys.argv[1] == "--email":
echo         print("📧 Email envoye aux administrateurs (si configures)")
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
echo.
echo %YELLOW%Note: L'alerte peut prendre quelques secondes a etre detectee%RESET%
echo %YELLOW%      Le notifier scrute la base toutes les 5 secondes%RESET%
pause
goto menu

:: ── 21. État du notifier ───────────────────────────────────────────────────
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
    
    set "CONFIG_DIR=%APPDATA%\IDS_Notifier"
    set "EMAIL_CONFIG=%CONFIG_DIR%\email_config.json"
    if exist "%EMAIL_CONFIG%" (
        echo 📧 Email: Configure
    ) else (
        echo 📧 Email: Non configure
    )
    echo.
   
    :: Afficher les dernières lignes du log
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

:: ── 22. Logs ──────────────────────────────────────────────────────────────
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
    echo    [E] Voir logs alertes critiques
    echo    [R] Retour
    echo.
    set /p log_choice="Choix (O/C/E/R) : "
    if /i "!log_choice!"=="O" notepad "%CONFIG_DIR%\notifier.log"
    if /i "!log_choice!"=="C" (
        echo. > "%CONFIG_DIR%\notifier.log"
        echo %GREEN%Logs effaces%RESET%
    )
    if /i "!log_choice!"=="E" (
        if exist "%CONFIG_DIR%\critical_alerts.log" notepad "%CONFIG_DIR%\critical_alerts.log"
        if not exist "%CONFIG_DIR%\critical_alerts.log" echo %YELLOW%Aucun log d'alerte critique%RESET%
    )
) else (
    echo %YELLOW%Aucun fichier de logs trouve%RESET%
    echo    Le notifier n'a peut-etre jamais ete lance
)
pause
goto menu

:: ── 23. Dossier de configuration ──────────────────────────────────────────
:config
echo.
echo %BLUE%[CONFIGURATION]%RESET%
set "CONFIG_DIR=%APPDATA%\IDS_Notifier"
if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"
explorer "%CONFIG_DIR%"
echo %GREEN%Dossier de configuration ouvert%RESET%
echo.
echo %YELLOW% Fichiers disponibles:%RESET%
echo    📄 notifier.conf : Configuration principale
echo    📄 .env : Variables d'environnement (DB)
echo    📄 email_config.json : Configuration email (optionnel)
echo    📄 notifier.log : Logs du notifier
echo    📄 critical_alerts.log : Alertes critiques
echo.
pause
goto menu

:: ── 24. Fin ─────────────────────────────────────────────────────────────────
:end
echo.
echo %BLUE%Merci d'avoir utilise IDS Notifier!%RESET%
echo.
exit /b 0