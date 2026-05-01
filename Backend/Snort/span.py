from netmiko import ConnectHandler

switch = {
    "device_type": "cisco_ios",
    "host": "10.10.10.50",
    "username": "admin",
    "password": "admin123",
    "secret": "cisco1",
    "port": 22,
    "global_delay_factor": 2,
    "disabled_algorithms": {"pubkeys": ["rsa-sha2-256", "rsa-sha2-512"]}
}

SOURCE_VLAN = "10"
DEST_PORT   = "GigabitEthernet1/0/8"   # ← port libre notconnect, branché à Snort

with ConnectHandler(**switch) as conn:
    conn.enable()

    # ── Appliquer le SPAN ──────────────────────────────────
    span_commands = [
        "no monitor session 1",
        f"monitor session 1 source vlan {SOURCE_VLAN} both",
        f"monitor session 1 destination interface {DEST_PORT}",
    ]

    output = conn.send_config_set(
        span_commands,
        read_timeout=30,        # évite le ReadTimeout
        cmd_verify=False        # ne vérifie pas le prompt après chaque commande
    )
    conn.save_config()
    print(output)

    print("\n--- Vérification SPAN ---")
    print(conn.send_command("show monitor session 1"))