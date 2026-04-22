from nornir import InitNornir
from nornir.core.inventory import Inventory, Host, Hosts, Groups, Defaults, ConnectionOptions
from nornir.core.plugins.inventory import InventoryPluginRegister
from nornir_netmiko.tasks import netmiko_send_config, netmiko_save_config
from nornir_utils.plugins.functions import print_result

# ─────────────────────────────────────────
#         CONFIGURATION SSH
# ─────────────────────────────────────────
SWITCH_IP     = "10.10.10.50"
SWITCH_USER   = "admin"
SWITCH_PASS   = "admin123"
SWITCH_SECRET = "cisco1"

# ─────────────────────────────────────────
#   CHOISIS TON INTERFACE ICI
#   Exemples : "GigabitEthernet1/0/1" ... "GigabitEthernet1/0/24"
# ─────────────────────────────────────────
INTERFACE  = "GigabitEthernet1/0/1"
VLAN_ID    = 17       # VLAN à assigner (10=reseau, 20=servers, 99=Quarantine...)
SHUTDOWN   = True      # True=shutdown 🔴  /  False=no shutdown 🟢

# ─────────────────────────────────────────
#         PORT SECURITY
# ─────────────────────────────────────────
PORT_SECURITY_ENABLE = True
MAX_MAC              = 2
VIOLATION_MODE       = "restrict"   # protect / restrict / shutdown
BPDU_GUARD           = True

# ─────────────────────────────────────────
#   Construction des commandes
# ─────────────────────────────────────────
def build_commands():
    cmds = [
        f"interface {INTERFACE}",
        "switchport mode access",
        f"switchport access vlan {VLAN_ID}",
        "shutdown" if SHUTDOWN else "no shutdown",
    ]

    if PORT_SECURITY_ENABLE:
        cmds += [
            "switchport port-security",
            f"switchport port-security maximum {MAX_MAC}",
            f"switchport port-security violation {VIOLATION_MODE}",
            "switchport port-security mac-address sticky",
        ]

    if BPDU_GUARD:
        cmds.append("spanning-tree bpduguard enable")

    cmds.append("exit")
    return cmds

# ─────────────────────────────────────────
#   Plugin inventaire en mémoire
# ─────────────────────────────────────────
class InMemoryInventory:
    def __init__(self, **kwargs): pass

    def load(self) -> Inventory:
        defaults = Defaults()
        h = Host(
            name="switch_cible",
            hostname=SWITCH_IP,
            username=SWITCH_USER,
            password=SWITCH_PASS,
            platform="ios",
            port=22,
            data={},
            groups=[],
            defaults=defaults,
            connection_options={
                "netmiko": ConnectionOptions(
                    extras={
                        "secret": SWITCH_SECRET,
                        "global_delay_factor": 2,
                        "disabled_algorithms": {
                            "pubkeys": ["rsa-sha2-256", "rsa-sha2-512"]
                        },
                    }
                )
            },
        )
        return Inventory(
            hosts=Hosts({"switch_cible": h}),
            groups=Groups(),
            defaults=defaults,
        )

InventoryPluginRegister.register("InMemoryInventory", InMemoryInventory)

# ─────────────────────────────────────────
#   Déploiement
# ─────────────────────────────────────────
def run_deploy():
    commands = build_commands()

    print(f"\n{'='*52}")
    print(f"  🔌 Connexion SSH via Nornir → {SWITCH_IP}")
    print(f"{'='*52}")
    print(f"  Interface  : {INTERFACE}")
    print(f"  VLAN       : {VLAN_ID}")
    print(f"  État       : {'SHUTDOWN 🔴' if SHUTDOWN else 'NO SHUTDOWN 🟢'}")
    print(f"  Port Sec   : {'✅ Activé' if PORT_SECURITY_ENABLE else '❌ Désactivé'}")
    if PORT_SECURITY_ENABLE:
        print(f"  Max MAC    : {MAX_MAC}")
        print(f"  Violation  : {VIOLATION_MODE.upper()}")
    print(f"  BPDU Guard : {'✅ Activé' if BPDU_GUARD else '❌ Désactivé'}")
    print(f"{'='*52}\n")

    print("📋 Commandes à envoyer :")
    for c in commands:
        print(f"   {c}")
    print()

    try:
        nr = InitNornir(
            runner={"plugin": "threaded", "options": {"num_workers": 1}},
            inventory={"plugin": "InMemoryInventory"},
        )

        print("✅ Nornir initialisé ! Envoi de la configuration...")
        result = nr.run(
            task=netmiko_send_config,
            config_commands=commands,
            name=f"Config {INTERFACE} → VLAN {VLAN_ID}",
        )

        if result.failed:
            exc = result["switch_cible"][0].exception
            print(f"❌ Erreur SSH : {exc}")
            return

        print("\n--- RÉSULTAT DU SWITCH ---")
        print_result(result)
        print("--------------------------\n")

        print("💾 Sauvegarde (write memory)...")
        nr.run(task=netmiko_save_config)
        print("🎉 Configuration appliquée et sauvegardée avec succès !")

    except Exception as e:
        print(f"❌ Erreur critique : {e}")

if __name__ == "__main__":
    run_deploy()