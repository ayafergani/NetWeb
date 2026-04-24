from nornir import InitNornir
from nornir_netmiko.tasks import netmiko_send_config, netmiko_save_config
from nornir_utils.plugins.functions import print_result
import os

def build_nornir():
    # Détermine le chemin absolu vers le dossier network pour trouver les fichiers YAML
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return InitNornir(
        runner={"plugin": "threaded", "options": {"num_workers": 1}},
        inventory={
            "plugin": "YAMLInventory",
            "options": {
                "host_file": os.path.join(base_dir, "hosts.yaml"),
                "group_file": os.path.join(base_dir, "groups.yaml"),    # optionnel
                "defaults_file": os.path.join(base_dir, "defaults.yaml") # optionnel
            }
        },
    )

def run_deploy(vlan_id, vlan_name, switch_ip=None, switch_user=None, switch_password=None):
    print("🔌 Connexion SSH via Nornir...")
    commands = [
        f"vlan {vlan_id}",
        f"name {vlan_name}",
        "exit"
    ]
    try:
        nr = build_nornir()
        print("✅ Nornir initialisé ! Envoi de la configuration VLAN...")
        
        # S'il y a des identifiants depuis l'interface, on met à jour Nornir dynamiquement
        if switch_ip:
            # On cible le premier switch de ton fichier hosts.yaml
            target_host = list(nr.inventory.hosts.keys())[0]
            nr.inventory.hosts[target_host].hostname = switch_ip
            if switch_user: nr.inventory.hosts[target_host].username = switch_user
            if switch_password: nr.inventory.hosts[target_host].password = switch_password
            
            # On filtre pour être sûr de ne déployer que sur ce switch spécifique
            nr = nr.filter(name=target_host)

        result = nr.run(
            task=netmiko_send_config,
            config_commands=commands,
            name=f"Création VLAN {vlan_id} - {vlan_name}"
        )

        if result.failed:
            # Récupère l'erreur de l'hôte qui a échoué
            for host, host_result in result.items():
                if host_result.failed:
                    exc = host_result[0].exception
                    print(f"❌ Erreur SSH sur {host} : {exc}")
                    return {"success": False, "error": f"Erreur SSH sur {host} : {exc}"}
            return {"success": False, "error": "Erreur inconnue lors du déploiement."}

        print("\n--- RÉSULTAT DU SWITCH ---")
        print_result(result)
        print("--------------------------")

        print("💾 Sauvegarde (write memory)...")
        nr.run(task=netmiko_save_config)
        print(f"🎉 VLAN {vlan_id} '{vlan_name}' créé et sauvegardé !")
        return {"success": True, "message": f"VLAN {vlan_id} '{vlan_name}' créé avec succès."}

    except Exception as e:
        print(f"❌ Erreur critique : {e}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    run_deploy(70, "Quarantine_Snort")