from flask import Blueprint, request, jsonify
from network.deploy_vlan import run_deploy
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

        # Mise à jour ou création de l'entrée
        if host_key not in hosts:
            hosts[host_key] = {"platform": "ios"}

        hosts[host_key]["hostname"] = hostname
        hosts[host_key]["username"] = username
        hosts[host_key]["password"] = password
        hosts[host_key]["port"]     = port

        # Mise à jour du enable secret dans connection_options
        if secret:
            hosts[host_key].setdefault("connection_options", {}) \
                           .setdefault("netmiko", {}) \
                           .setdefault("extras", {})["secret"] = secret

        _save_hosts(hosts)
        return jsonify({"success": True, "message": "hosts.yaml mis à jour avec succès."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── Déploiement direct (sans BDD) ─────────────────────────────────────────────
@network_bp.route("/api/network/deploy-vlan/direct", methods=["POST"])
def api_deploy_vlan_direct():
    """Déploie un VLAN directement sur le switch (hosts.yaml, sans BDD)."""
    data      = request.json or {}
    vlan_id   = data.get("vlan_id") or data.get("id")
    vlan_name = data.get("vlan_name") or data.get("name") or data.get("nom")

    if not vlan_id or not vlan_name:
        return jsonify({"success": False, "error": "L'ID et le nom du VLAN sont requis."}), 400

    try:
        result = run_deploy(int(vlan_id), str(vlan_name))
        return jsonify(result), 200 if result.get("success") else 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500