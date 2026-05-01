from flask import Blueprint, request, jsonify
from network.deploy_vlan import run_deploy as run_deploy_vlan
from network.interface_deploy import run_deploy as run_deploy_interface
import yaml, os

network_bp = Blueprint('network', __name__)

HOSTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "network", "hosts.yaml")


def _load_hosts():
    with open(HOSTS_FILE, "r") as f:
        return yaml.safe_load(f) or {}


def _save_hosts(data):
    with open(HOSTS_FILE, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


# ── Lire la config du switch depuis hosts.yaml ────────────────────────────────
@network_bp.route("/api/network/switch-config", methods=["GET"])
def get_switch_config():
    """Retourne les infos du switch stockées dans hosts.yaml."""
    try:
        hosts = _load_hosts()
        switches = []
        for host_key, host_val in hosts.items():
            conn = (host_val.get("connection_options") or {}).get("netmiko", {}).get("extras", {})
            switches.append({
                "host_key":  host_key,
                "hostname":  host_val.get("hostname", ""),
                "username":  host_val.get("username", ""),
                "password":  host_val.get("password", ""),
                "platform":  host_val.get("platform", "ios"),
                "port":      host_val.get("port", 22),
                "secret":    conn.get("secret", ""),
            })
        return jsonify({"success": True, "switches": switches})
    except FileNotFoundError:
        return jsonify({"success": False, "error": "hosts.yaml introuvable"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── Mettre à jour la config du switch dans hosts.yaml ────────────────────────
@network_bp.route("/api/network/switch-config", methods=["POST"])
def update_switch_config():
    """
    Met à jour hosts.yaml avec les nouvelles infos SSH.
    Body attendu : { host_key, hostname, username, password, port, secret }
    """
    data = request.json or {}
    host_key = data.get("host_key", "switch_cible")
    hostname = data.get("hostname", "").strip()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    port     = int(data.get("port", 22))
    secret   = data.get("secret", "").strip()

    if not hostname or not username:
        return jsonify({"success": False, "error": "hostname et username sont requis"}), 400

    try:
        try:
            hosts = _load_hosts()
        except FileNotFoundError:
            hosts = {}

        if host_key not in hosts:
            hosts[host_key] = {"platform": "ios"}

        hosts[host_key]["hostname"] = hostname
        hosts[host_key]["username"] = username
        hosts[host_key]["password"] = password
        hosts[host_key]["port"]     = port

        if secret:
            hosts[host_key].setdefault("connection_options", {}) \
                           .setdefault("netmiko", {}) \
                           .setdefault("extras", {})["secret"] = secret

        _save_hosts(hosts)
        return jsonify({"success": True, "message": "hosts.yaml mis à jour avec succès."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── Déploiement VLAN direct (sans BDD) ───────────────────────────────────────
@network_bp.route("/api/network/deploy-vlan/direct", methods=["POST"])
def api_deploy_vlan_direct():
    """Déploie un VLAN directement sur le switch (hosts.yaml, sans BDD)."""
    data      = request.json or {}
    vlan_id   = data.get("vlan_id") or data.get("id")
    vlan_name = data.get("vlan_name") or data.get("name") or data.get("nom")

    if not vlan_id or not vlan_name:
        return jsonify({"success": False, "error": "L'ID et le nom du VLAN sont requis."}), 400

    try:
        result = run_deploy_vlan(int(vlan_id), str(vlan_name))
        return jsonify(result), 200 if result.get("success") else 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── Déploiement Interface sur le switch via SSH ───────────────────────────────
@network_bp.route("/api/network/deploy-interface", methods=["POST"])
def api_deploy_interface():
    """
    Déploie la configuration d'une interface sur le switch Cisco via SSH/Nornir.
    Les identifiants SSH sont lus automatiquement depuis network/hosts.yaml.

    Body JSON attendu :
        interface_name  (str)  ex. "GigabitEthernet1/0/1"
        mode            (str)  "access" | "trunk"
        vlan_id         (int)  VLAN ID (ignoré si mode=trunk)
        status          (str)  "UP" | "DOWN"
        port_security   (bool) activer le port-security
        max_mac         (int)  max adresses MAC
        violation_mode  (str)  "protect" | "restrict" | "shutdown"
        bpdu_guard      (bool) activer le BPDU Guard
        allowed_vlans   (str)  VLANs trunk autorisés ex. "10,20,30" ou "all"
        description     (str)  description du port (optionnel)
    """
    data = request.json or {}

    interface_name = data.get("interface_name", "").strip()
    if not interface_name:
        return jsonify({"success": False, "error": "interface_name est requis."}), 400

    mode          = str(data.get("mode", "access")).strip().lower()
    vlan_id_raw   = data.get("vlan_id")
    status        = str(data.get("status", "UP")).strip().upper()
    port_security = bool(data.get("port_security", False))
    max_mac       = int(data.get("max_mac", 1))
    violation     = str(data.get("violation_mode", "shutdown")).strip().lower()
    bpdu_guard    = bool(data.get("bpdu_guard", False))
    allowed_vlans = data.get("allowed_vlans") or None
    description   = data.get("description") or None
    static_mac    = (data.get("static_mac") or "").strip() or None

    # Validation basique
    if mode not in ("access", "trunk"):
        return jsonify({"success": False, "error": "mode doit être 'access' ou 'trunk'."}), 400

    if status not in ("UP", "DOWN"):
        return jsonify({"success": False, "error": "status doit être 'UP' ou 'DOWN'."}), 400

    try:
        vlan_id = int(vlan_id_raw) if vlan_id_raw is not None else None
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "vlan_id doit être un entier."}), 400

    if mode == "access" and not vlan_id:
        return jsonify({"success": False, "error": "vlan_id est requis en mode access."}), 400

    try:
        result = run_deploy_interface(
            interface_name=interface_name,
            mode=mode,
            vlan_id=vlan_id,
            status=status,
            port_security=port_security,
            max_mac=max_mac,
            violation_mode=violation,
            bpdu_guard=bpdu_guard,
            allowed_vlans=allowed_vlans,
            description=description,
            static_mac=static_mac,
        )
        http_code = 200 if result.get("success") else 500
        return jsonify(result), http_code
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── Suppression / Reset d'une interface sur le switch ────────────────────────
@network_bp.route("/api/network/reset-interface", methods=["POST"])
def api_reset_interface():
    """
    Remet une interface à sa configuration par défaut sur le switch Cisco.
    Supprime : port-security, BPDU guard, description, remet en access VLAN 1, shutdown.

    Body JSON attendu :
        interface_name  (str)  ex. "GigabitEthernet1/0/1"
    """
    data = request.json or {}
    interface_name = data.get("interface_name", "").strip()
    if not interface_name:
        return jsonify({"success": False, "error": "interface_name est requis."}), 400

    reset_commands = [
        f"interface {interface_name}",
        "no description",
        "switchport mode access",
        "switchport access vlan 1",
        "no switchport port-security",
        "no switchport port-security maximum",
        "no switchport port-security violation",
        "no switchport port-security mac-address sticky",
        "no spanning-tree bpduguard enable",
        "shutdown",
        "exit",
    ]

    try:
        from network.interface_deploy import build_nornir
        from nornir_netmiko.tasks import netmiko_send_config, netmiko_save_config

        nr = build_nornir()
        if not nr.inventory.hosts:
            return jsonify({
                "success": False,
                "error": "Aucun host trouvé dans hosts.yaml.",
                "commands": reset_commands,
            }), 500

        result = nr.run(
            task=netmiko_send_config,
            config_commands=reset_commands,
            name=f"Reset {interface_name}",
        )

        if result.failed:
            errors = []
            for host, host_result in result.items():
                if host_result.failed:
                    errors.append(f"Erreur SSH sur {host} : {host_result[0].exception}")
            return jsonify({
                "success": False,
                "error": " | ".join(errors) or "Erreur inconnue.",
                "commands": reset_commands,
            }), 500

        nr.run(task=netmiko_save_config)
        return jsonify({
            "success": True,
            "message": f"Interface {interface_name} réinitialisée et sauvegardée sur le switch.",
            "commands": reset_commands,
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e), "commands": reset_commands}), 500

# ── TFTP Backup : copy running-config → serveur TFTP ─────────────────────────
@network_bp.route("/api/network/tftp-backup", methods=["POST"])
def api_tftp_backup():
    """
    Sauvegarde la running-config du switch vers un serveur TFTP.

    Body JSON attendu :
        tftp_server  (str)  IP du serveur TFTP  ex. "192.168.1.100"
        filename     (str)  Nom du fichier       ex. "running-config.cfg"
    """
    data        = request.json or {}
    tftp_server = data.get("tftp_server", "").strip()
    filename    = data.get("filename",    "running-config.cfg").strip()

    if not tftp_server:
        return jsonify({"success": False, "error": "tftp_server est requis."}), 400

    try:
        from network.interface_deploy import build_nornir
        from nornir.core.task import Task, Result

        nr = build_nornir()
        if not nr.inventory.hosts:
            return jsonify({"success": False, "error": "Aucun host dans hosts.yaml."}), 500

        all_output = []

        def tftp_backup_task(task: Task) -> Result:
            conn = task.host.get_connection("netmiko", task.nornir.config)
            # Commande non-interactive grâce à l'URL complète
            cmd = f"copy running-config tftp://{tftp_server}/{filename}"
            output = conn.send_command_timing(cmd, delay_factor=3, max_loops=150)
            # Certains IOS demandent encore une confirmation du nom de fichier
            if "Destination filename" in output or "filename" in output.lower():
                output += conn.send_command_timing(filename, delay_factor=3, max_loops=150)
            if "?" in output or "confirm" in output.lower():
                output += conn.send_command_timing("\n", delay_factor=2)
            all_output.append(output)
            if "Error" in output or "error" in output.lower():
                raise Exception(output.strip())
            return Result(host=task.host, result=output)

        result = nr.run(task=tftp_backup_task, name="TFTP Backup")

        if result.failed:
            errors = [str(r[0].exception) for _, r in result.items() if r.failed]
            return jsonify({"success": False, "error": " | ".join(errors), "output": "\n".join(all_output)}), 500

        return jsonify({
            "success": True,
            "message": f"running-config sauvegardée → tftp://{tftp_server}/{filename}",
            "output": "\n".join(all_output),
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── TFTP Restore : copy TFTP → running-config ────────────────────────────────
@network_bp.route("/api/network/tftp-restore", methods=["POST"])
def api_tftp_restore():
    """
    Restaure la configuration du switch depuis un serveur TFTP.

    Body JSON attendu :
        tftp_server  (str)  IP du serveur TFTP  ex. "192.168.1.100"
        filename     (str)  Nom du fichier       ex. "running-config.cfg"
    """
    data        = request.json or {}
    tftp_server = data.get("tftp_server", "").strip()
    filename    = data.get("filename",    "running-config.cfg").strip()

    if not tftp_server:
        return jsonify({"success": False, "error": "tftp_server est requis."}), 400

    try:
        from network.interface_deploy import build_nornir
        from nornir.core.task import Task, Result

        nr = build_nornir()
        if not nr.inventory.hosts:
            return jsonify({"success": False, "error": "Aucun host dans hosts.yaml."}), 500

        all_output = []

        def tftp_restore_task(task: Task) -> Result:
            conn = task.host.get_connection("netmiko", task.nornir.config)
            cmd = f"copy tftp://{tftp_server}/{filename} running-config"
            output = conn.send_command_timing(cmd, delay_factor=3, max_loops=150)
            # Confirmer le nom de fichier destination si demandé
            if "Destination filename" in output or "filename" in output.lower():
                output += conn.send_command_timing("\n", delay_factor=3, max_loops=150)
            if "confirm" in output.lower() or "?" in output:
                output += conn.send_command_timing("\n", delay_factor=2)
            all_output.append(output)
            if "Error" in output or "error" in output.lower():
                raise Exception(output.strip())
            return Result(host=task.host, result=output)

        result = nr.run(task=tftp_restore_task, name="TFTP Restore")

        if result.failed:
            errors = [str(r[0].exception) for _, r in result.items() if r.failed]
            return jsonify({"success": False, "error": " | ".join(errors), "output": "\n".join(all_output)}), 500

        return jsonify({
            "success": True,
            "message": f"Configuration restaurée depuis tftp://{tftp_server}/{filename} → running-config.",
            "output": "\n".join(all_output),
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500