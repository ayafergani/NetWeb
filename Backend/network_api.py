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
        )
        http_code = 200 if result.get("success") else 500
        return jsonify(result), http_code
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500