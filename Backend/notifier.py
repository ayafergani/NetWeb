"""
IDS Alert Notifier - Surveillance en arrière-plan (Windows)
============================================================
Lance ce script une fois → il tourne en tâche de fond et envoie
des notifications Windows toast à chaque nouvelle alerte détectée,
même si le dashboard est fermé.
 
Dépendances :
    pip install plyer requests psycopg2-binary win10toast-persist
 
Usage :
    python notifier.py
    python notifier.py --api http://localhost:5000    (URL Flask personnalisée)
    python notifier.py --interval 5                   (polling toutes les 5s)
    python notifier.py --db                           (connexion directe DB, sans Flask)
"""

import argparse
import sys
import time
import logging
import threading
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────
CONFIG_DIR = Path(os.getenv("APPDATA")) / "IDS_Notifier"
CONFIG_DIR.mkdir(exist_ok=True)
STATE_FILE = CONFIG_DIR / "notifier_state.json"
LOG_FILE = CONFIG_DIR / "notifier.log"

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("ids-notifier")


# ── Gestion d'état persistant ───────────────────────────────────────────────
def load_state():
    """Charge le dernier ID vu depuis le fichier d'état"""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                return set(state.get('seen_ids', [])), state.get('last_check', 0)
        except:
            pass
    return set(), 0

def save_state(seen_ids):
    """Sauvegarde les IDs vus"""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump({
                'seen_ids': list(seen_ids),
                'last_check': time.time()
            }, f)
    except Exception as e:
        log.error(f"Erreur sauvegarde état: {e}")

def get_machine_guid():
    """Identifiant unique pour éviter les doublons sur multi-sessions"""
    import winreg
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                            r"SOFTWARE\Microsoft\Cryptography")
        guid, _ = winreg.QueryValueEx(key, "MachineGuid")
        return guid
    except:
        return "default"


# ── Notification Windows améliorée (multi-méthodes) ─────────────────────────
class WindowsNotifier:
    def __init__(self):
        self.notification_id = 1
        self.last_toast_time = {}
        
    def _get_toast_priority(self, severity):
        """Définit la priorité selon la sévérité"""
        priorities = {
            "critical": "required",
            "medium": "high", 
            "low": "normal"
        }
        return priorities.get(severity, "normal")
    
    def _notify_winrt(self, title, message, severity="normal"):
        """Utilise Windows.Runtime (plus moderne et fiable)"""
        try:
            import asyncio
            from winrt.windows.ui.notifications import (
                ToastNotificationManager, ToastNotification, 
                ToastTemplateType, ToastDuration
            )
            from winrt.windows.data.xml.dom import XmlDocument
            
            # Créer le template
            template = ToastTemplateType.TOAST_TEXT02
            toast_xml = ToastNotificationManager.get_template_content(template)
            
            # Remplir les textes
            xml_doc = XmlDocument()
            xml_doc.load_xml(toast_xml)
            text_nodes = xml_doc.get_elements_by_tag_name("text")
            text_nodes[0].append_child(xml_doc.create_text_node(title))
            text_nodes[1].append_child(xml_doc.create_text_node(message))
            
            # Configurer la durée et la priorité
            duration = ToastDuration.SHORT
            if severity == "critical":
                duration = ToastDuration.LONG
                
            toast = ToastNotification(xml_doc)
            toast.expiration_time = datetime.now() + timedelta(seconds=30)
            
            # Afficher
            notifier = ToastNotificationManager.create_toast_notifier("IDS Monitor")
            notifier.show(toast)
            return True
        except Exception as e:
            log.debug(f"WinRT failed: {e}")
            return False
    
    def _notify_win10toast(self, title, message, severity="normal"):
        """Utilise win10toast-persist pour notifications persistantes"""
        try:
            from win10toast_persist import ToastNotifier
            
            duration = 10 if severity == "critical" else 6
            icon_path = Path(__file__).parent / "icon.ico"
            icon = str(icon_path) if icon_path.exists() else None
            
            toaster = ToastNotifier()
            toaster.show_toast(
                title, message,
                icon_path=icon,
                duration=duration,
                threaded=True
            )
            return True
        except Exception as e:
            log.debug(f"win10toast failed: {e}")
            return False
    
    def _notify_plyer(self, title, message, severity="normal"):
        """Fallback avec plyer"""
        try:
            from plyer import notification
            notification.notify(
                title=title[:64],
                message=message[:256],
                app_name="IDS Monitor",
                app_icon=None,
                timeout=8,
                ticker="IDS Alert"
            )
            return True
        except Exception as e:
            log.debug(f"Plyer failed: {e}")
            return False
    
    def _notify_winotify(self, title, message, severity="normal"):
        """Utilise winotify pour plus de contrôle"""
        try:
            from winotify import Notification, audio
            
            notif = Notification(
                app_id="IDS Monitor",
                title=title[:64],
                msg=message[:256],
                duration="long" if severity == "critical" else "short"
            )
            
            if severity == "critical":
                notif.set_audio(audio.Default, loop=False)
                
            notif.show()
            return True
        except Exception as e:
            log.debug(f"Winotify failed: {e}")
            return False
    
    def _notify_messagebox(self, title, message, severity="normal"):
        """Dernier recours : MessageBox"""
        try:
            import ctypes
            flags = 0x40 | 0x40000  # Info + Topmost
            if severity == "critical":
                flags = 0x30 | 0x40000  # Warning + Topmost
            ctypes.windll.user32.MessageBoxW(0, message[:256], title[:64], flags)
            return True
        except:
            return False
    
    def notify(self, title, message, severity="normal"):
        """Envoie une notification en essayant plusieurs méthodes"""
        # Éviter les notifications en rafale (max 1 par 2 secondes)
        current_time = time.time()
        if title in self.last_toast_time:
            if current_time - self.last_toast_time[title] < 2:
                return
        
        methods = [
            self._notify_winrt,
            self._notify_win10toast,
            self._notify_winotify,
            self._notify_plyer,
            self._notify_messagebox
        ]
        
        for method in methods:
            if method(title, message, severity):
                self.last_toast_time[title] = current_time
                return True
        
        log.error("Aucune méthode de notification n'a fonctionné")
        return False


# ── Sons d'alerte personnalisés ─────────────────────────────────────────────
def play_alert_sound(severity="normal"):
    """Joue un son selon la sévérité de l'alerte"""
    try:
        import winsound
        sounds = {
            "critical": (1000, 500),  # (fréquence, durée ms)
            "medium": (800, 300),
            "low": (600, 200),
            "normal": (500, 150)
        }
        freq, duration = sounds.get(severity, (500, 150))
        winsound.Beep(freq, duration)
    except:
        pass


# ════════════════════════════════════════════════════════════════════════════
#  MODE 1 — Surveillance via l'API Flask
# ════════════════════════════════════════════════════════════════════════════
def watch_api(api_base: str, interval: int, notifier: WindowsNotifier):
    import requests
    
    log.info(f"Démarrage surveillance API → {api_base}  (toutes les {interval}s)")
    seen_ids, last_check = load_state()
    first_run = len(seen_ids) == 0
    
    # Tester la connexion API
    max_retries = 5
    for i in range(max_retries):
        try:
            resp = requests.get(f"{api_base}/api/health", timeout=5)
            if resp.status_code == 200:
                log.info(f"✅ API accessible : {api_base}")
                break
        except:
            if i < max_retries - 1:
                log.warning(f"⏳ Attente API... ({i+1}/{max_retries})")
                time.sleep(3)
            else:
                log.error(f"❌ API injoignable après {max_retries} tentatives: {api_base}")
                log.error("Vérifiez que le dashboard Flask est lancé (python app.py)")
                if not args.db:
                    sys.exit(1)
    
    consecutive_errors = 0
    
    while True:
        try:
            resp = requests.get(
                f"{api_base}/api/alerts",
                params={"limit": 200, "sort": "newest"},
                timeout=8,
            )
            resp.raise_for_status()
            data = resp.json()
            consecutive_errors = 0
            
            if not data.get("success"):
                log.warning(f"API : succès=False → {data.get('error')}")
            else:
                alerts = data.get("alerts", [])
                new_alerts = [a for a in alerts if a["id"] not in seen_ids]
                
                if new_alerts:
                    log.info(f"📨 {len(new_alerts)} nouvelle(s) alerte(s) détectée(s)")
                    
                    for a in sorted(new_alerts, key=lambda x: x.get("timestamp", "")):
                        seen_ids.add(a["id"])
                        
                        # Priorité aux alertes critiques
                        sev = a.get("severity", "low")
                        if sev == "critical":
                            threading.Thread(target=play_alert_sound, args=("critical",), daemon=True).start()
                            threading.Thread(target=_handle_new_alert, args=(a, notifier), daemon=True).start()
                            # Notification supplémentaire après 2s pour les critiques
                            time.sleep(2)
                            threading.Thread(target=_handle_new_alert, args=(a, notifier), daemon=True).start()
                        else:
                            threading.Thread(target=_handle_new_alert, args=(a, notifier), daemon=True).start()
                    
                    # Sauvegarder l'état périodiquement
                    if len(seen_ids) % 10 == 0:
                        save_state(seen_ids)
                
                elif not first_run:
                    # Affichage périodique du statut
                    if int(time.time()) % 60 == 0:  # Toutes les minutes
                        log.info(f"💓 Surveillance active - {len(seen_ids)} alertes traitées")
                
                first_run = False
                
        except requests.exceptions.ConnectionError:
            consecutive_errors += 1
            if consecutive_errors == 1:
                log.warning(f"⚠️ API inaccessible ({api_base})")
            elif consecutive_errors % 10 == 0:
                log.warning(f"⚠️ API toujours inaccessible - {consecutive_errors} erreurs")
        except Exception as e:
            log.error(f"Erreur inattendue : {e}")
        
        # Sauvegarde périodique
        if int(time.time()) % 300 == 0:  # Toutes les 5 minutes
            save_state(seen_ids)
        
        time.sleep(interval)


# ════════════════════════════════════════════════════════════════════════════
#  MODE 2 — Surveillance directe en base (sans Flask)
# ════════════════════════════════════════════════════════════════════════════
def watch_db(interval: int, notifier: WindowsNotifier):
    try:
        import psycopg2
        import psycopg2.extras
        from psycopg2 import OperationalError
    except ImportError:
        log.error("psycopg2 introuvable. Lancez : pip install psycopg2-binary")
        sys.exit(1)
    
    db_cfg = {
        "dbname":   os.getenv("DB_NAME", "ids_db"),
        "user":     os.getenv("DB_USER", "aya"),
        "password": os.getenv("DB_PASSWORD", "aya"),
        "host":     os.getenv("DB_HOST", "192.168.1.2"),
        "port":     os.getenv("DB_PORT", "5432"),
    }
    
    log.info(f"Démarrage surveillance DB directe → {db_cfg['host']}:{db_cfg['port']}/{db_cfg['dbname']}")
    
    seen_ids, _ = load_state()
    first_run = len(seen_ids) == 0
    consecutive_failures = 0
    
    # Tester la connexion DB
    for i in range(3):
        try:
            test_conn = psycopg2.connect(**db_cfg, connect_timeout=5)
            test_conn.close()
            log.info(f"✅ Base de données accessible : {db_cfg['host']}/{db_cfg['dbname']}")
            break
        except OperationalError as e:
            if i < 2:
                log.warning(f"⏳ Attente DB... ({i+1}/3) : {e}")
                time.sleep(5)
            else:
                log.error(f"❌ Base de données injoignable : {e}")
                log.error("Vérifiez que PostgreSQL est lancé et les identifiants corrects")
                sys.exit(1)
    
    while True:
        try:
            conn = psycopg2.connect(**db_cfg, connect_timeout=5)
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cur.execute("""
                SELECT id, timestamp, source_ip, destination_ip,
                       source_port, destination_port,
                       attack_type, severity, protocol, details
                FROM alertes
                WHERE timestamp > NOW() - INTERVAL '%s seconds'
                ORDER BY timestamp DESC
                LIMIT 500
            """, (interval * 3,))
            
            rows = cur.fetchall()
            conn.close()
            consecutive_failures = 0
            
            new_rows = [r for r in rows if r["id"] not in seen_ids]
            
            if new_rows:
                log.info(f"📨 {len(new_rows)} nouvelle(s) alerte(s) détectée(s) dans la DB")
                
                for r in sorted(new_rows, key=lambda x: x.get("timestamp") or datetime.min):
                    seen_ids.add(r["id"])
                    
                    # Convertir le format
                    sev_raw = (r["severity"] or "").lower()
                    if sev_raw in ("critical", "critique", "high", "élevée", "elevee"):
                        sev = "critical"
                    elif sev_raw in ("medium", "moyen", "moyenne"):
                        sev = "medium"
                    else:
                        sev = "low"
                    
                    src_ip = r['source_ip'] or "0.0.0.0"
                    src_port = r['source_port']
                    dst_ip = r['destination_ip'] or "0.0.0.0"
                    dst_port = r['destination_port']
                    
                    src = f"{src_ip}:{src_port}" if src_port else src_ip
                    dst = f"{dst_ip}:{dst_port}" if dst_port else dst_ip
                    
                    alert = {
                        "id": r["id"],
                        "name": r["attack_type"] or "Attaque inconnue",
                        "severity": sev,
                        "src": src,
                        "dst": dst,
                        "proto": r["protocol"] or "N/A",
                        "timestamp": r["timestamp"].isoformat() if r["timestamp"] else "",
                        "details": r.get("details", {})
                    }
                    
                    if sev == "critical":
                        threading.Thread(target=play_alert_sound, args=("critical",), daemon=True).start()
                    
                    threading.Thread(target=_handle_new_alert, args=(alert, notifier), daemon=True).start()
                    
                    # Sauvegarde périodique
                    if len(seen_ids) % 10 == 0:
                        save_state(seen_ids)
            
            elif not first_run:
                if int(time.time()) % 60 == 0:
                    log.info(f"💓 Surveillance active - {len(seen_ids)} alertes en base")
            
            first_run = False
            save_state(seen_ids)
            
        except OperationalError as e:
            consecutive_failures += 1
            if consecutive_failures == 1:
                log.warning(f"⚠️ Connexion DB perdue : {e}")
            elif consecutive_failures % 5 == 0:
                log.warning(f"⚠️ DB toujours inaccessible ({consecutive_failures} erreurs)")
        except Exception as e:
            log.error(f"Erreur DB inattendue : {e}")
        
        time.sleep(interval)


# ════════════════════════════════════════════════════════════════════════════
#  Traitement d'une nouvelle alerte
# ════════════════════════════════════════════════════════════════════════════
# Couleurs console
SEV_COLOR = {
    "critical": "\033[91m",
    "medium":   "\033[93m",
    "low":      "\033[92m",
}
RESET = "\033[0m"

SEV_LABEL = {
    "critical": "🔴 CRITIQUE",
    "medium":   "🟡 MOYEN",
    "low":      "🔵 FAIBLE",
}

def _handle_new_alert(alert: dict, notifier: WindowsNotifier):
    sev = alert.get("severity", "low")
    name = alert.get("name", "Alerte inconnue")
    src = alert.get("src", "?")
    dst = alert.get("dst", "?")
    proto = alert.get("proto", "N/A")
    ts = alert.get("timestamp", "")
    
    color = SEV_COLOR.get(sev, "")
    label = SEV_LABEL.get(sev, sev.upper())
    
    # Log console coloré avec timestamp
    timestamp = datetime.now().strftime("%H:%M:%S")
    log.info(f"{color}[{timestamp}] ⚠ {label} | {name} | {src} → {dst} ({proto}){RESET}")
    
    # Préparer la notification Windows
    icons = {
        "critical": "⚠️🚨",
        "medium": "⚠️",
        "low": "ℹ️"
    }
    
    title = f"{icons.get(sev, '🔔')} IDS - {label}"
    
    message_lines = [
        f"📋 {name}",
        f"📡 {src} → {dst} [{proto}]"
    ]
    
    if ts:
        try:
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            message_lines.append(f"🕐 {dt.strftime('%H:%M:%S')}")
        except:
            pass
    
    # Ajouter les détails si disponibles
    details = alert.get("details")
    if details and isinstance(details, dict):
        if "payload" in details:
            message_lines.append(f"📦 Payload: {details['payload'][:50]}...")
        if "signature" in details:
            message_lines.append(f"🔍 Sig: {details['signature'][:40]}...")
    
    message = "\n".join(message_lines)
    
    # Envoyer la notification (dans un thread séparé)
    def send():
        for attempt in range(2):
            if notifier.notify(title, message, sev):
                break
            if attempt == 0:
                time.sleep(0.5)
    
    threading.Thread(target=send, daemon=True).start()
    
    # Pour les alertes critiques, écrire dans un fichier d'urgence
    if sev == "critical":
        try:
            with open(CONFIG_DIR / "critical_alerts.log", "a", encoding="utf-8") as f:
                f.write(f"{datetime.now().isoformat()} | {name} | {src} -> {dst}\n")
        except:
            pass


# ════════════════════════════════════════════════════════════════════════════
#  Point d'entrée
# ════════════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(
        description="IDS Windows Background Notifier",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--api",
        default="http://localhost:5000",
        help="URL de base de l'API Flask (défaut: http://localhost:5000)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Intervalle de polling en secondes (défaut: 5)",
    )
    parser.add_argument(
        "--db",
        action="store_true",
        help="Mode connexion directe à la base (sans Flask)",
    )
    parser.add_argument(
        "--sound",
        action="store_true",
        default=True,
        help="Activer les sons d'alerte (défaut: activé)",
    )
    args = parser.parse_args()
    
    log.info("=" * 60)
    log.info("🛡️ IDS Background Notifier v2.0 - Démarrage")
    log.info(f"📁 Dossier config: {CONFIG_DIR}")
    log.info("=" * 60)
    
    notifier = WindowsNotifier()
    
    try:
        if args.db:
            watch_db(args.interval, notifier)
        else:
            watch_api(args.api, args.interval, notifier)
    except KeyboardInterrupt:
        log.info("🛑 Notifier arrêté par l'utilisateur.")
        save_state(set())
        sys.exit(0)
    except Exception as e:
        log.error(f"💥 Erreur fatale: {e}")
        save_state(set())
        sys.exit(1)

if __name__ == "__main__":
    main()