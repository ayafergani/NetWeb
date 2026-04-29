@echo off
title SNORT IDS - Installation service automatique
echo.
echo ============================================
echo   SNORT IDS - Installation demarrage auto
echo ============================================
echo.

:: Installer dependances
echo [1/3] Installation Flask...
pip install flask flask-cors --quiet
echo       OK.

:: Creer le script VBS qui lance Python sans fenetre
echo [2/3] Creation du lanceur invisible...
echo Set WshShell = CreateObject("WScript.Shell") > "%APPDATA%\snort_launcher.vbs"
echo WshShell.Run "python ""C:\Users\HP\Downloads\NetWeb\Backend\log.py""", 0, False >> "%APPDATA%\snort_launcher.vbs"
echo       OK.

:: Ajouter au demarrage automatique de Windows
echo [3/3] Ajout au demarrage de Windows...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "SnortIDS" /t REG_SZ /d "\"%APPDATA%\snort_launcher.vbs\"" /f >nul
echo       OK.

:: Lancer maintenant sans attendre le redemarrage
echo.
echo Lancement immediat du serveur...
start "" wscript.exe "%APPDATA%\snort_launcher.vbs"
timeout /t 3 /nobreak >nul

echo.
echo ============================================
echo   INSTALLATION TERMINEE !
echo.
echo   - Serveur demarre maintenant
echo   - Demarre automatiquement a chaque
echo     allumage de votre PC
echo   - Ouvrez simplement le fichier HTML
echo     quand vous voulez voir les logs
echo ============================================
echo.
echo Appuyez sur une touche pour ouvrir l'interface...
pause >nul
start "" "C:\Users\HP\Downloads\NetWeb\Frontend\logs (2).html"