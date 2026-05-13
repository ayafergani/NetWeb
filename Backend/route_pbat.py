"""
==============================================================
  À AJOUTER dans ton app.py Flask
  Route : POST /api/run-pbat
  Lance p.bat avec l'option choisie depuis le navigateur.
==============================================================
"""

import os
import subprocess
import json
import tempfile
from flask import request, jsonify

# Chemin vers p.bat — adapte si besoin
PBAT_PATH = os.path.join(os.path.dirname(__file__), 'p.bat')


@app.route('/api/run-pbat', methods=['POST'])
def run_pbat():
    """
    Lance p.bat avec l'option voulue.

    Corps JSON attendu :
      { "option": "1" }                          → Installer le notifier
      { "option": "8", "params": { ... } }       → Configurer les emails

    Pour l'option 8, les params sont écrits dans email_config.json
    AVANT de lancer p.bat, pour éviter l'interaction au terminal.
    """
    data   = request.get_json(force=True, silent=True) or {}
    option = str(data.get('option', '')).strip()
    params = data.get('params', {})

    if option not in ('1', '8'):
        return jsonify({'success': False, 'message': 'Option invalide (1 ou 8 uniquement)'}), 400

    if not os.path.isfile(PBAT_PATH):
        return jsonify({'success': False, 'message': f'p.bat introuvable : {PBAT_PATH}'}), 500

    # ── Option 8 : écrire la config email AVANT de lancer p.bat ──────────────
    if option == '8':
        config_dir  = os.path.join(os.getenv('APPDATA', ''), 'IDS_Notifier')
        os.makedirs(config_dir, exist_ok=True)
        email_config = {
            'smtp_server':  params.get('server',   ''),
            'smtp_port':    int(params.get('port', 587)),
            'smtp_user':    params.get('user',     ''),
            'smtp_password': params.get('password', ''),
            'use_tls':      True,
            'from_email':   params.get('user',     ''),
            'from_name':    params.get('fromname', 'IDS Monitoring System'),
        }
        config_file = os.path.join(config_dir, 'email_config.json')
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(email_config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            return jsonify({'success': False, 'message': f'Impossible d\'écrire email_config.json : {e}'}), 500

        # Lancer p.bat option 8 en mode silencieux (la config est déjà écrite)
        # On envoie "3" (Retour) automatiquement car la config existe déjà
        input_sequence = f'8\n3\n'
    else:
        # Option 1 : installation normale, on envoie juste le choix
        input_sequence = '1\n'

    try:
        proc = subprocess.Popen(
            ['cmd.exe', '/c', PBAT_PATH],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,   # pas de fenêtre console
        )
        stdout, stderr = proc.communicate(input=input_sequence, timeout=60)

        if proc.returncode not in (0, None):
            return jsonify({
                'success': False,
                'message': f'p.bat a retourné le code {proc.returncode}',
                'stderr':  stderr[:500]
            }), 500

        label = 'Notifier installé' if option == '1' else 'Configuration email appliquée'
        return jsonify({'success': True, 'message': label, 'output': stdout[:500]})

    except subprocess.TimeoutExpired:
        proc.kill()
        return jsonify({'success': False, 'message': 'p.bat a dépassé le délai (60s)'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
