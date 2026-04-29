# ============================================================
# SCRIPT 2 — Appliquer le Port Mirroring (SPAN)
# ============================================================
from netmiko import ConnectHandler

switch = {
    "device_type": "cisco_ios",
    "host": "10.10.10.50",
    "username": "admin",
    "password": "admin123",
    "secret": "cisco1",
    "port": 22,
    "global_delay_factor": 2,
    "disabled_algorithms": {
        "pubkeys": ["rsa-sha2-256", "rsa-sha2-512"]
    }
}

# ─── Adapter ces valeurs selon résultats étape 1 ───────────
SOURCE_PORTS = ["GigabitEthernet0/1",
                "GigabitEthernet0/2",
                "GigabitEthernet0/3"]   # ports à surveiller
DEST_PORT    = "GigabitEthernet0/4"    # port connecté à Snort
# ───────────────────────────────────────────────────────────

span_commands = ["no monitor session 1"]  # reset propre

for port in SOURCE_PORTS:
    span_commands.append(
        f"monitor session 1 source interface {port} both"
    )

span_commands.append(
    f"monitor session 1 destination interface {DEST_PORT} encapsulation replicate"
)

with ConnectHandler(**switch) as conn:
    conn.enable()
    output = conn.send_config_set(span_commands)
    conn.save_config()
    print(output)
    print("\n--- Vérification SPAN ---")
    print(conn.send_command("show monitor session 1"))