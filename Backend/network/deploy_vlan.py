from nornir import InitNornir
from nornir_netmiko.tasks import netmiko_send_config, netmiko_save_config
from nornir_utils.plugins.functions import print_result

VLAN_ID   = 70
VLAN_NAME = "Quarantine_Snort"

commands = [
    f"vlan {VLAN_ID}",
    f"name {VLAN_NAME}",
    "exit"
]

def build_nornir():
    return InitNornir(
        runner={"plugin": "threaded", "options": {"num_workers": 1}},
        inventory={
            "plugin": "YAMLInventory",
            "options": {
                "host_file": "hosts.yaml",
                "group_file": "groups.yaml",    # optionnel
                "defaults_file": "defaults.yaml" # optionnel
            }
        },
    )

def run_deploy():
    print("🔌 Connexion SSH via Nornir...")
    try:
        nr = build_nornir()
        print("✅ Nornir initialisé ! Envoi de la configuration VLAN...")

        result = nr.run(
            task=netmiko_send_config,
            config_commands=commands,
            name=f"Création VLAN {VLAN_ID} - {VLAN_NAME}"
        )

        if result.failed:
            exc = result["switch_cible"][0].exception
            print(f"❌ Erreur SSH : {exc}")
            return

        print("\n--- RÉSULTAT DU SWITCH ---")
        print_result(result)
        print("--------------------------")

        print("💾 Sauvegarde (write memory)...")
        nr.run(task=netmiko_save_config)
        print(f"🎉 VLAN {VLAN_ID} '{VLAN_NAME}' créé et sauvegardé !")

    except Exception as e:
        print(f"❌ Erreur critique : {e}")

if __name__ == "__main__":
    run_deploy()