"""
run_bat_api.py
──────────────
Blueprint Flask qui expose la route POST /api/run-pbat
appelée par topbar.js pour lancer p.bat (options 1 et 8)
EN TANT QU'ADMINISTRATEUR (élévation UAC via ShellExecuteW).

Placement : même dossier que app.py et p.bat
"""

import os
import sys
import json
import logging

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

run_bat_bp = Blueprint("run_bat", __name__)

# Chemin absolu vers p.bat (même dossier que ce fichier)
BAT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "p.bat")

# Options autorisées
ALLOWED_OPTIONS = {"1", "8"}


# ────────────────────────────────────────────────────────────────
# Helper : écriture config email
# ────────────────────────────────────────────────────────────────

def _write_email_config(params: dict) -> str:
    config_dir = os.path.join(
        os.environ.get("APPDATA", os.path.expanduser("~")),
        "IDS_Notifier"
    )
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(config_dir, "email_config.json")

    config = {
        "smtp_server":   params.get("server", ""),
        "smtp_port":     int(params.get("port", 587)),
        "smtp_user":     params.get("user", ""),
        "smtp_password": params.get("password", ""),
        "use_tls":       True,
        "from_email":    params.get("user", ""),
        "from_name":     params.get("fromname", "IDS Monitoring System"),
    }

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

    logger.info("email_config.json écrit dans %s", config_path)
    return config_path


# ────────────────────────────────────────────────────────────────
# Helper : lancement p.bat EN ADMINISTRATEUR
# ────────────────────────────────────────────────────────────────

def _launch_bat_as_admin(option: str) -> None:
    if not os.path.isfile(BAT_PATH):
        raise FileNotFoundError(f"p.bat introuvable : {BAT_PATH}")

    if sys.platform != "win32":
        raise OSError("Le lancement de p.bat en admin n'est supporté que sur Windows.")

    import ctypes

    SW_SHOWNORMAL = 1

    ret = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        "cmd.exe",
        f'/c start "IDS Notifier Option {option}" "{BAT_PATH}"',
        os.path.dirname(BAT_PATH),
        SW_SHOWNORMAL,
    )

    if ret <= 32:
        error_codes = {
            0:  "Mémoire insuffisante ou ressources épuisées",
            2:  "Fichier introuvable",
            3:  "Chemin introuvable",
            5:  "Accès refusé — UAC annulée ou droits insuffisants",
            8:  "Mémoire insuffisante",
            32: "DLL partagée introuvable",
        }
        msg = error_codes.get(ret, f"Erreur ShellExecute inconnue (code {ret})")
        raise RuntimeError(msg)

    logger.info("p.bat lancé en admin (option %s) — ShellExecuteW code=%d", option, ret)


# ────────────────────────────────────────────────────────────────
# Route principale
# ────────────────────────────────────────────────────────────────

@run_bat_bp.route("/api/run-pbat", methods=["POST"])
def run_pbat():
    payload = request.get_json(silent=True) or {}
    option  = str(payload.get("option", "")).strip()
    params  = payload.get("params") or {}

    if option not in ALLOWED_OPTIONS:
        return jsonify(
            success=False,
            message=f"Option invalide : '{option}'. Valeurs acceptées : {', '.join(sorted(ALLOWED_OPTIONS))}"
        ), 400

    if not os.path.isfile(BAT_PATH):
        return jsonify(
            success=False,
            message=f"p.bat introuvable sur le serveur ({BAT_PATH})"
        ), 404

    # Option 8 : écrire la config email AVANT de lancer p.bat
    if option == "8":
        required = ["server", "user", "password"]
        missing  = [k for k in required if not str(params.get(k, "")).strip()]
        if missing:
            return jsonify(
                success=False,
                message=f"Champs manquants pour la config email : {', '.join(missing)}"
            ), 422
        try:
            _write_email_config(params)
        except Exception as exc:
            logger.exception("Impossible d'écrire email_config.json")
            return jsonify(
                success=False,
                message=f"Erreur écriture config email : {exc}"
            ), 500

    # Lancement de p.bat EN ADMIN
    try:
        _launch_bat_as_admin(option)
    except FileNotFoundError as exc:
        return jsonify(success=False, message=str(exc)), 404
    except OSError as exc:
        return jsonify(success=False, message=str(exc)), 500
    except RuntimeError as exc:
        return jsonify(
            success=False,
            message=f"Lancement annulé ou refusé : {exc}"
        ), 500
    except Exception as exc:
        logger.exception("Erreur inattendue au lancement de p.bat")
        return jsonify(
            success=False,
            message=f"Erreur inattendue : {exc}"
        ), 500

    messages = {
        "1": "Notifier IDS en cours d'installation (option 1) ✅",
        "8": "Configuration email appliquée et notifier lancé (option 8) ✅",
    }
    return jsonify(success=True, message=messages[option])