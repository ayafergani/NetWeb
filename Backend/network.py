from netmiko import ConnectHandler

print("🚀 Initialisation de l'automatisation via Câble Console...")

# On configure la connexion pour utiliser le câble bleu (Serial) au lieu de SSH
switch = {
    'device_type': 'cisco_ios_serial',
    'serial_settings': {
        'port': 'COM5',  # REMPLACE PAR TON PORT (ex: COM4, COM5...)
        'baudrate': 9600,
        'bytesize': 8,
        'parity': 'N',
        'stopbits': 1
    },
    # Pas besoin d'IP ! Le câble va direct au switch.
}

# Les commandes qu'on veut pousser
commands = [
    "vlan 99",
    "name Quarantine_Snort",
    "exit"
]

try:
    print(f"📡 Connexion au port {switch['serial_settings']['port']} en cours...")
    # On se connecte
    net_connect = ConnectHandler(**switch)
    
    # On appuie sur "Entrée" pour réveiller la console
    net_connect.write_channel('\r')
    
    print("✅ Connecté ! Envoi de la configuration...")
    # On pousse les commandes
    output = net_connect.send_config_set(commands)
    
    # On sauvegarde (write memory)
    save_out = net_connect.save_config()
    
    print("\n--- Résultat du Déploiement ---")
    print(output)
    print("-------------------------------")
    print("🎉 SUCCÈS ! Le VLAN a été créé via le câble Console !")
    
    net_connect.disconnect()

except Exception as e:
    print(f"❌ Erreur : {e}")