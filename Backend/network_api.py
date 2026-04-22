from flask import Blueprint, request, jsonify
from network.deploy_vlan import run_deploy

network_bp = Blueprint('network', __name__)

@network_bp.route("/api/network/deploy-vlan", methods=["POST"])
def api_deploy_vlan():
    """Route pour déployer un VLAN directement sur le switch (Mode Dev - Sans BDD)"""
    data = request.json
    vlan_id = data.get("vlan_id")
    vlan_name = data.get("vlan_name")
    
    # Récupération des infos SSH saisies dans l'interface
    switch_ip = data.get("switch_ip")
    switch_user = data.get("switch_user")
    switch_password = data.get("switch_password")

    if not vlan_id or not vlan_name:
        return jsonify({"success": False, "error": "L'ID et le nom du VLAN sont requis."}), 400

    try:
        # Appel direct avec les paramètres dynamiques
        result = run_deploy(vlan_id, vlan_name, switch_ip, switch_user, switch_password)
        
        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500