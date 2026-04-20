from flask import Blueprint, request, jsonify
from utils.decorators import require_role
from nornir import InitNornir
from nornir_netmiko.tasks import netmiko_send_config, netmiko_save_config

network_bp = Blueprint('network', __name__)

@network_bp.route("/api/vlans", methods=["POST"])
@require_role("ADMIN") # Ou NETWORK_ADMIN
def create_vlan_on_switch():
    data = request.json
    vlan_id = data.get("id")
    vlan_name = data.get("name")

    # Nouveaux paramètres dynamiques
    host = data.get("switchIp")
    username = data.get("switchUser")
    password = data.get("switchPass")

    if not all([vlan_id, vlan_name, host, username, password]):
        return jsonify({"error": "Paramètres VLAN et identifiants du switch requis"}), 400

    try:
        # 1. Création d'un inventaire Nornir à la volée
        inventory = {
            "plugin": "DictInventory",
            "options": {
                "hosts": {
                    "switch_cible": {
                        "hostname": host,
                        "username": username,
                        "password": password,
                        "platform": "ios" # plate-forme Cisco IOS
                    }
                }
            }
        }

        # 2. Initialisation de Nornir
        nr = InitNornir(inventory=inventory)
        
        # 3. Exécution de la tâche de configuration
        commands = [f"vlan {vlan_id}", f"name {vlan_name}"]
        result = nr.run(task=netmiko_send_config, config_commands=commands)
        nr.run(task=netmiko_save_config) # write memory

        if result.failed:
            return jsonify({"error": f"Erreur SSH: {result['switch_cible'][0].exception}"}), 500

        output = result["switch_cible"][0].result
        return jsonify({"message": "VLAN créé avec succès via Nornir", "output": output}), 200
    except Exception as e:
        return jsonify({"error": f"Erreur critique de Nornir : {str(e)}"}), 500