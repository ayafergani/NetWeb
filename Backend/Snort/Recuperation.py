# snort_manager_windows.py
#!/usr/bin/env python3
import subprocess
import time
import threading
import re
import os
import sys
from datetime import datetime
import psutil  # pip install psutil

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Database.db import get_db_connection as connect_db


class SnortManager:
    def __init__(self, interface="5", log_dir="C:\\Snort\\log"):
        """
        Args:
            interface: Nom de l'interface réseau Windows (ex: "Ethernet", "Wi-Fi")
            log_dir: Dossier des logs Snort
        """
        self.interface = interface
        self.log_dir = log_dir
        self.alert_file = os.path.join(log_dir, "alert")  # Format fast alert
        self.snort_process = None
        self.snort_running = False
        self.alert_count = 0
        self.db_connection = None
        self.db_cursor = None
        self.db_insert_count = 0
        self.packet_count = 0
        
        # Créer le dossier des logs
        os.makedirs(log_dir, exist_ok=True)
        
        # Nettoyer l'ancien fichier d'alertes
        if os.path.exists(self.alert_file):
            try:
                os.remove(self.alert_file)
            except:
                pass
        
        self.init_database()
    
    def init_database(self):
        """Initialise la connexion PostgreSQL"""
        try:
            self.db_connection = connect_db()
            if self.db_connection:
                self.db_cursor = self.db_connection.cursor()
                print("✅ Connexion à PostgreSQL établie")
                self.create_tables_if_not_exists()
        except Exception as e:
            print(f"⚠️ Base de données non disponible: {e}")
    
    def create_tables_if_not_exists(self):
        """Crée les tables nécessaires si elles n'existent pas"""
        try:
            self.db_cursor.execute("""
                CREATE TABLE IF NOT EXISTS alertes (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source_ip INET,
                    destination_ip INET,
                    attack_type VARCHAR(500),
                    severity VARCHAR(50),
                    detection_engine VARCHAR(100),
                    details TEXT,
                    protocol VARCHAR(10),
                    source_port INTEGER,
                    destination_port INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.db_connection.commit()
            print("✅ Tables vérifiées/créées")
        except Exception as e:
            print(f"⚠️ Erreur création table: {e}")
    
    def convert_timestamp(self, timestamp_str):
        """Convertit le timestamp Snort (MM/DD-HH:MM:SS) en format PostgreSQL"""
        try:
            # Format Snort: "04/29-10:30:45.123456"
            date_part, time_part = timestamp_str.split('-')
            month, day = date_part.split('/')
            year = datetime.now().year
            # Prendre seulement les 8 premiers caractères pour HH:MM:SS
            time_clean = time_part[:8] if len(time_part) >= 8 else time_part
            return f"{year}-{month}-{day} {time_clean}"
        except:
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def convert_severity(self, severity_value):
        """Convertit le niveau de priorité Snort en texte"""
        if severity_value == 0 or severity_value == 1:
            return 'élevée'
        elif severity_value == 2:
            return 'moyenne'
        elif severity_value == 3:
            return 'basse'
        return 'inconnue'
    
    def parse_alert(self, header_line, ip_line):
        """Parse une alerte Snort format fast"""
        timestamp = ""
        ts_match = re.search(r'(\d{2}/\d{2}-\d{2}:\d{2}:\d{2}\.\d+)', ip_line)
        if ts_match:
            timestamp = ts_match.group(1)
        else:
            timestamp = datetime.now().strftime("%m/%d-%H:%M:%S")
        
        sid = ""
        sid_match = re.search(r'\[(\d+:\d+:\d+)\]', header_line)
        if sid_match:
            sid = sid_match.group(1)
        
        msg = ""
        msg_match = re.search(r'\[\*\*\] \[[0-9:]+\] (.*) \[\*\*\]', header_line)
        if msg_match:
            msg = msg_match.group(1).strip()
        
        priority = 0
        prio_match = re.search(r'Priority: (\d+)', header_line)
        if prio_match:
            priority = int(prio_match.group(1))
        
        proto = ""
        proto_match = re.search(r'\{([^}]+)\}', ip_line)
        if proto_match:
            proto = proto_match.group(1)
        
        # Extraction IP:Port (format: 10.10.10.1:12345 -> 10.10.10.2:80)
        ip_ports = re.findall(r'(\d+\.\d+\.\d+\.\d+):(\d+)', ip_line)
        
        src_ip = None
        src_port = None
        dst_ip = None
        dst_port = None
        
        if len(ip_ports) >= 1:
            src_ip = ip_ports[0][0]
            src_port = int(ip_ports[0][1]) if ip_ports[0][1].isdigit() else None
        if len(ip_ports) >= 2:
            dst_ip = ip_ports[1][0]
            dst_port = int(ip_ports[1][1]) if ip_ports[1][1].isdigit() else None
        
        return {
            'timestamp_raw': timestamp,
            'timestamp': self.convert_timestamp(timestamp),
            'sid': sid,
            'src_ip': src_ip,
            'dst_ip': dst_ip,
            'attack_type': msg,
            'severity': priority,
            'protocol': proto,
            'src_port': src_port,
            'dst_port': dst_port,
            'detection_engine': sid.split(':')[0] if sid else 'Snort'
        }
    
    def save_to_db(self, alert):
        """Sauvegarde l'alerte dans PostgreSQL"""
        if not self.db_connection:
            return False
        
        try:
            severity_text = self.convert_severity(alert['severity'])
            
            attack_type = alert['attack_type']
            if attack_type and len(attack_type) > 200:
                attack_type = attack_type[:200]
            
            details = alert['attack_type']
            if details and len(details) > 500:
                details = details[:500]
            
            self.db_cursor.execute("""
                INSERT INTO alertes (
                    timestamp, source_ip, destination_ip,
                    attack_type, severity, detection_engine,
                    details, protocol, source_port, destination_port
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                alert['timestamp'],
                alert['src_ip'],
                alert['dst_ip'],
                attack_type,
                severity_text,
                alert['detection_engine'],
                details,
                alert['protocol'],
                alert['src_port'],
                alert['dst_port']
            ))
            self.db_connection.commit()
            self.db_insert_count += 1
            return True
        except Exception as e:
            print(f"   ❌ Erreur DB: {e}")
            try:
                self.db_connection.rollback()
            except:
                pass
            return False
    
    def start_snort(self):
        """Démarre Snort sur Windows"""
        try:
            # Commande Snort pour Windows (format fast alert)
            cmd = f'C:\\Snort\\bin\\snort.exe -A console -c C:\\Snort\\etc\\snort.conf -i {self.interface} -l "{self.log_dir}"'
            
            print(f"\n{'=' * 80}")
            print(f"🔍 SNORT - SURVEILLANCE RÉSEAU (Windows)")
            print(f"{'=' * 80}")
            print(f"📡 Interface: {self.interface}")
            print(f"📁 Logs: {self.log_dir}")
            print(f"💾 Base de données: {'✅ Activée' if self.db_connection else '❌ Désactivée'}")
            print(f"{'=' * 80}\n")
            
            # Démarrer Snort sans fenêtre
            self.snort_process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            self.snort_running = True
            
            # Thread pour surveiller les alertes
            thread = threading.Thread(target=self._tail_alerts, daemon=True)
            thread.start()
            
            # Thread pour les statistiques paquets (Windows)
            stats_thread = threading.Thread(target=self._update_packet_stats_windows, daemon=True)
            stats_thread.start()
            
            return True
        except Exception as e:
            print(f"❌ Erreur démarrage Snort: {e}")
            return False
    
    def _update_packet_stats_windows(self):
        """Met à jour le compteur de paquets sur Windows via psutil"""
        last_bytes_sent = {}
        last_bytes_recv = {}
        
        while self.snort_running:
            try:
                # Obtenir les stats réseau via psutil
                net_stats = psutil.net_io_counters(pernic=True)
                
                if self.interface in net_stats:
                    current_recv = net_stats[self.interface].bytes_recv
                    current_sent = net_stats[self.interface].bytes_sent
                    
                    # Calculer la différence approximative en paquets
                    # (basé sur taille moyenne de paquet estimée à 1500 bytes)
                    if self.interface in last_bytes_recv:
                        diff_bytes = current_recv - last_bytes_recv[self.interface]
                        estimated_packets = diff_bytes // 1500  # Approximation
                        if estimated_packets > 0:
                            self.packet_count += estimated_packets
                    
                    last_bytes_recv[self.interface] = current_recv
                    last_bytes_sent[self.interface] = current_sent
                
            except Exception as e:
                pass
            
            time.sleep(5)
    
    def _tail_alerts(self):
        """Surveille le fichier d'alertes en temps réel"""
        time.sleep(2)
        
        while self.snort_running and self.snort_process and self.snort_process.poll() is None:
            if os.path.exists(self.alert_file):
                try:
                    with open(self.alert_file, 'r', encoding='utf-8', errors='ignore') as f:
                        f.seek(0, os.SEEK_END)
                        while self.snort_running:
                            line = f.readline()
                            if not line:
                                time.sleep(0.1)
                                continue
                            
                            line = line.strip()
                            if not line:
                                continue
                            
                            if "[**]" in line:
                                header_line = line
                                next_line = f.readline().strip()
                                if next_line:
                                    self.alert_count += 1
                                    alert = self.parse_alert(header_line, next_line)
                                    severity_text = self.convert_severity(alert['severity'])
                                    
                                    # Affichage coloré dans la console
                                    print(f"\n\033[91m🚨 ALERTE #{self.alert_count}: {alert['attack_type']} [{severity_text}]\033[0m")
                                    print(f"   📍 {alert['src_ip']}:{alert['src_port']} -> {alert['dst_ip']}:{alert['dst_port']}")
                                    
                                    # Sauvegarde en BDD
                                    if self.db_connection:
                                        self.save_to_db(alert)
                except Exception as e:
                    print(f"⚠️ Erreur lecture alertes: {e}")
            else:
                time.sleep(1)
    
    def stop_snort(self):
        """Arrête Snort proprement"""
        try:
            if self.snort_process:
                self.snort_process.terminate()
                try:
                    self.snort_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.snort_process.kill()
        except:
            pass
        
        self.snort_running = False
        self.snort_process = None
        print(f"\n🛑 Snort arrêté")
        print(f"📊 Statistiques finales:")
        print(f"   - Alertes détectées: {self.alert_count}")
        print(f"   - Alertes sauvegardées: {self.db_insert_count}")
        print(f"   - Paquets estimés: {self.packet_count}")
    
    def is_running(self):
        return self.snort_running
    
    def get_packet_count(self):
        return self.packet_count
    
    def get_alert_count(self):
        return self.alert_count


# Gestionnaire global
_snort_manager = None


def start_snort(interface="Ethernet"):
    """Démarre Snort (fonction externe)"""
    global _snort_manager
    if _snort_manager is None:
        _snort_manager = SnortManager(interface=interface)
    return _snort_manager.start_snort()


def stop_snort():
    """Arrête Snort (fonction externe)"""
    global _snort_manager
    if _snort_manager:
        _snort_manager.stop_snort()
        _snort_manager = None


def get_packet_count():
    """Retourne le nombre de paquets (fonction externe)"""
    global _snort_manager
    if _snort_manager:
        return _snort_manager.get_packet_count()
    return 0


def get_alert_count():
    """Retourne le nombre d'alertes (fonction externe)"""
    global _snort_manager
    if _snort_manager:
        return _snort_manager.get_alert_count()
    return 0


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Snort Manager Windows")
    parser.add_argument("--interface", default="Ethernet", help="Nom de l'interface réseau")
    parser.add_argument("--log-dir", default="C:\\Snort\\log", help="Dossier des logs")
    
    args = parser.parse_args()
    
    manager = SnortManager(interface=args.interface, log_dir=args.log_dir)
    try:
        manager.start_snort()
        print("Snort en cours d'exécution. Appuyez sur Ctrl+C pour arrêter.")
        while manager.is_running():
            time.sleep(1)
            # Afficher statut périodique
            if manager.alert_count > 0:
                print(f"\r📊 Alertes: {manager.alert_count} | DB: {manager.db_insert_count}", end="")
    except KeyboardInterrupt:
        print("\n\nArrêt demandé...")
        manager.stop_snort()