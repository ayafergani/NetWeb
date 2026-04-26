from nornir import InitNornir
from nornir_netmiko.tasks import netmiko_send_config, netmiko_save_config
from nornir_utils.plugins.functions import print_result
import os

def build_nornir():
    """
    Initialise Nornir en lisant automatiquement hosts.yaml (et optionnellement
    groups.yaml / defaults.yaml) situés dans le même dossier que ce fichier.
    Aucune info SSH manuelle n'est nécessaire : tout est dans hosts.yaml.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    hosts_file    = os.path.join(base_dir, "hosts.yaml")
    groups_file   = os.path.join(base_dir, "groups.yaml")
    defaults_file = os.path.join(base_dir, "defaults.yaml")

    inventory_options = {"host_file": hosts_file}
    if os.path.exists(groups_file):
        inventory_options["group_file"] = groups_file
    if os.path.exists(defaults_file):
        inventory_options["defaults_file"] = defaults_file

    return InitNornir(
        runner={"plugin": "threaded", "options": {"num_workers": 1}},
        inventory={"plugin": "YAMLInventory", "options": inventory_options},
    )


def run_deploy(vlan_id, vlan_name, switch_ip=None, switch_user=None, switch_password=None):
    """
    Déploie un VLAN sur le switch Cisco via SSH/Netmiko.

    Les identifiants SSH sont lus AUTOMATIQUEMENT depuis hosts.yaml.
    Les paramètres switch_ip / switch_user / switch_password sont conservés
    pour compatibilité ascendante mais ignorés en fonctionnement normal.

    Retourne : {"success": bool, "message"/"error": str}
    """
    print(f"🔌 Connexion SSH au switch (source : hosts.yaml)...")

    commands = [
        f"vlan {vlan_id}",
        f"name {vlan_name}",
        "exit",
    ]

    try:
        nr = build_nornir()

        if not nr.inventory.hosts:
            return {
                "success": False,
                "error": "Aucun host trouvé dans hosts.yaml. Vérifiez le fichier d'inventaire."
            }

        print(f"✅ Inventaire chargé. Switches : {list(nr.inventory.hosts.keys())}")
        print(f"📡 Envoi de la config VLAN {vlan_id} ({vlan_name})...")

        result = nr.run(
            task=netmiko_send_config,
            config_commands=commands,
            name=f"Création VLAN {vlan_id} - {vlan_name}",
        )

        if result.failed:
            errors = []
            for host, host_result in result.items():
                if host_result.failed:
                    exc = host_result[0].exception
                    print(f"❌ Erreur SSH sur {host} : {exc}")
                    errors.append(f"Erreur SSH sur {host} : {exc}")
            return {"success": False, "error": " | ".join(errors) or "Erreur inconnue."}

        print("\n--- RÉSULTAT SWITCH ---")
        print_result(result)
        print("-----------------------")

        print("💾 Sauvegarde (write memory)...")
        nr.run(task=netmiko_save_config)

        print(f"🎉 VLAN {vlan_id} '{vlan_name}' créé et sauvegardé !")
        return {
            "success": True,
            "message": f"VLAN {vlan_id} '{vlan_name}' créé et sauvegardé sur le switch."
        }

    except FileNotFoundError as e:
        msg = f"Fichier d'inventaire introuvable : {e}"
        print(f"❌ {msg}")
        return {"success": False, "error": msg}

    except Exception as e:
        print(f"❌ Erreur critique : {e}")
        return {"success": False, "error": str(e)}


# ─── Test manuel ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Crée le VLAN 70 "Quarantine_Snort" sur le switch défini dans hosts.yaml
    result = run_deploy(70, "Quarantine_Snort")
    print(result)