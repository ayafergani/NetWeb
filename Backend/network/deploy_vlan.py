from netmiko import ConnectHandler
import time

# --- CONFIGURATION CONSOLE ---
# Remplace 'COM3' par ton numéro de port (vérifie dans le Gestionnaire de périphériques)
device = {
    'device_type': 'cisco_ios_serial',
    'serial_settings': {
        'port': 'COM5', 
        'baudrate': 9600,
    }
}

# La liste des commandes pour créer ton VLAN
commands = [
    "vlan 99",
    "name Quarantine_Snort",
    "exit"
]

def run_backup_deploy():
    try:
        print("🔌 Tentative de connexion via le câble Console...")
        
        # On se connecte
        with ConnectHandler(**device) as net_connect:
            # On envoie un retour à la ligne pour réveiller le switch
            net_connect.write_channel('\r')
            time.sleep(1)
            
            print("✅ Console détectée ! Envoi de la configuration...")
            
            # On envoie les commandes de VLAN
            output = net_connect.send_config_set(commands)
            
            # On sauvegarde
            print("💾 Sauvegarde en cours (write memory)...")
            save_out = net_connect.save_config()
            
            print("\n--- RÉSULTAT DU SWITCH ---")
            print(output)
            print("--------------------------")
            print("🎉 VICTOIRE ! Le VLAN 99 a été créé via l'automatisation Console.")

    except Exception as e:
        print(f"❌ Erreur critique : {e}")
        print("\n💡 ASTUCE : Vérifie que PuTTY est bien FERMÉ et que le port COM est le bon !")

if __name__ == "__main__":
    run_backup_deploy()