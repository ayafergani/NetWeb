from flask import Blueprint, jsonify, request
from Database.db import get_db_connection
import psycopg2.extras
import logging

interface_bp = Blueprint("interface", __name__)
logger = logging.getLogger(__name__)


def generate_default_interfaces():
    interfaces = []
    interface_id = 1

    for port_number in range(1, 25):
        is_configured = port_number <= 4 or port_number == 24
        interfaces.append({
            "id_interface": interface_id,
            "nom": f"Gi1/0/{port_number}",
            "ip": "192.168.1.10" if port_number == 4 else None,
            "vlan_id": 20 if port_number == 3 else (30 if port_number == 24 else 10 if is_configured else 1),
            "equipement_id": None,
            "status": "UP" if port_number <= 4 else "DOWN",
            "mode": "Access",
            "speed": "1Gb" if port_number <= 4 else None,
            "allowed_vlans": None,
            "port_security": port_number <= 3,
            "max_mac": 1,
            "violation_mode": "shutdown",
            "bpdu_guard": True,
            "type": "access",
        })
        interface_id += 1

    for port_number in range(1, 5):
        is_configured = port_number <= 2
        interfaces.append({
            "id_interface": interface_id,
            "nom": f"Te1/1/{port_number}",
            "ip": None,
            "vlan_id": None if is_configured else 1,
            "equipement_id": None,
            "status": "UP" if port_number == 1 else "DOWN",
            "mode": "Trunk" if is_configured else "Access",
            "speed": "10Gb" if port_number == 1 else None,
            "allowed_vlans": "all" if is_configured else None,
            "port_security": False,
            "max_mac": 1,
            "violation_mode": "shutdown",
            "bpdu_guard": False,
            "type": "uplink",
        })
        interface_id += 1

    return interfaces


def ensure_interface_schema():
    conn = get_db_connection()

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'interface'
        """)
        columns = {row[0] for row in cur.fetchall()}

        if "bpd_u_guard" in columns and "bpdu_guard" not in columns:
            cur.execute("ALTER TABLE interface RENAME COLUMN bpd_u_guard TO bpdu_guard")
            conn.commit()
            logger.info("Colonne interface.bpd_u_guard renommee en bpdu_guard")
    except Exception:
        conn.rollback()
        logger.exception("Erreur lors de la verification du schema interface")
        raise
    finally:
        conn.close()


def initialize_default_interfaces():
    ensure_interface_schema()
    default_interfaces = generate_default_interfaces()
    conn = get_db_connection()
    inserted_count = 0

    try:
        cur = conn.cursor()
        cur.execute("SELECT id_eq FROM equipement ORDER BY id_eq ASC LIMIT 1")
        equipment_row = cur.fetchone()
        default_equipment_id = equipment_row[0] if equipment_row else None

        for item in default_interfaces:
            cur.execute("SELECT 1 FROM interface WHERE nom = %s", (item["nom"],))
            if cur.fetchone():
                continue

            cur.execute("""
                INSERT INTO interface (
                    id_interface, nom, ip, vlan_id, equipement_id, status, mode,
                    speed, allowed_vlans, port_security, max_mac, violation_mode,
                    bpdu_guard, type
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                item["id_interface"],
                item["nom"],
                item["ip"],
                item["vlan_id"],
                item["equipement_id"] if item["equipement_id"] is not None else default_equipment_id,
                item["status"],
                item["mode"],
                item["speed"],
                item["allowed_vlans"],
                item["port_security"],
                item["max_mac"],
                item["violation_mode"],
                item["bpdu_guard"],
                item["type"],
            ))
            inserted_count += 1

        conn.commit()
        logger.info("Initialisation interfaces Cisco 9200 terminee: %s nouvelles interfaces", inserted_count)
        return inserted_count
    except Exception:
        conn.rollback()
        logger.exception("Erreur lors de l'initialisation des interfaces par defaut")
        raise
    finally:
        conn.close()


def row_to_interface(row):
    return {
        "id_interface": row["id_interface"],
        "nom": row["nom"],
        "ip": row["ip"],
        "vlan_id": row["vlan_id"],
        "equipement_id": row["equipement_id"],
        "status": row["status"],
        "mode": row["mode"],
        "speed": row["speed"],
        "allowed_vlans": row["allowed_vlans"],
        "port_security": row["port_security"],
        "max_mac": row["max_mac"],
        "violation_mode": row["violation_mode"],
        "bpdu_guard": row["bpdu_guard"],
        "type": row["type"],
    }


def normalize_interface_payload(data, forced_id=None):
    if not isinstance(data, dict):
        raise ValueError("Le corps JSON est invalide")

    raw_id = forced_id if forced_id is not None else data.get("id_interface")
    try:
        id_interface = int(raw_id)
    except (TypeError, ValueError):
        raise ValueError("id_interface doit etre un entier")

    raw_vlan_id = data.get("vlan_id")
    vlan_id = None if raw_vlan_id in (None, "", "All") else raw_vlan_id
    if vlan_id is not None:
        try:
            vlan_id = int(vlan_id)
        except (TypeError, ValueError):
            raise ValueError("vlan_id doit etre un entier")

    raw_equipement_id = data.get("equipement_id")
    equipement_id = None if raw_equipement_id in (None, "") else raw_equipement_id
    if equipement_id is not None:
        try:
            equipement_id = int(equipement_id)
        except (TypeError, ValueError):
            raise ValueError("equipement_id doit etre un entier")

    raw_max_mac = data.get("max_mac", 1)
    max_mac = 1 if raw_max_mac in (None, "") else raw_max_mac
    try:
        max_mac = int(max_mac)
    except (TypeError, ValueError):
        raise ValueError("max_mac doit etre un entier")

    payload = {
        "id_interface": id_interface,
        "nom": str(data.get("nom", "")).strip(),
        "ip": str(data.get("ip", "")).strip() or None,
        "vlan_id": vlan_id,
        "equipement_id": equipement_id,
        "status": str(data.get("status", "DOWN")).strip().upper() or "DOWN",
        "mode": str(data.get("mode", "Access")).strip().capitalize() or "Access",
        "speed": str(data.get("speed", "")).strip() or None,
        "allowed_vlans": str(data.get("allowed_vlans", "")).strip() or None,
        "port_security": bool(data.get("port_security", False)),
        "max_mac": max_mac,
        "violation_mode": str(data.get("violation_mode", "shutdown")).strip().lower() or "shutdown",
        "bpdu_guard": bool(data.get("bpdu_guard", False)),
        "type": str(data.get("type", "access")).strip().lower() or "access",
    }

    if not payload["nom"]:
        raise ValueError("Le nom de l'interface est requis")
    if payload["status"] not in ("UP", "DOWN"):
        raise ValueError("status doit etre UP ou DOWN")
    if payload["mode"] not in ("Access", "Trunk"):
        raise ValueError("mode doit etre Access ou Trunk")
    if payload["type"] not in ("access", "trunk", "uplink"):
        raise ValueError("type doit etre access, trunk ou uplink")
    if payload["max_mac"] < 1:
        raise ValueError("max_mac doit etre superieur ou egal a 1")

    return payload


@interface_bp.route("/api/interface", methods=["GET"])
def get_interfaces():
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT id_interface, nom, ip, vlan_id, equipement_id, status, mode,
                   speed, allowed_vlans, port_security, max_mac, violation_mode,
                   bpdu_guard, type
            FROM interface
            ORDER BY id_interface ASC
        """)
        rows = cur.fetchall()
        interfaces = [row_to_interface(row) for row in rows]
        return jsonify({"success": True, "count": len(interfaces), "interfaces": interfaces})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()


@interface_bp.route("/api/interface", methods=["POST"])
def create_interface():
    try:
        payload = normalize_interface_payload(request.get_json())
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT 1 FROM interface WHERE id_interface = %s", (payload["id_interface"],))
        if cur.fetchone():
            return jsonify({"success": False, "error": f"Interface {payload['id_interface']} existe deja"}), 409

        cur.execute("""
            INSERT INTO interface (
                id_interface, nom, ip, vlan_id, equipement_id, status, mode,
                speed, allowed_vlans, port_security, max_mac, violation_mode,
                bpdu_guard, type
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id_interface, nom, ip, vlan_id, equipement_id, status, mode,
                      speed, allowed_vlans, port_security, max_mac, violation_mode,
                      bpdu_guard, type
        """, (
            payload["id_interface"],
            payload["nom"],
            payload["ip"],
            payload["vlan_id"],
            payload["equipement_id"],
            payload["status"],
            payload["mode"],
            payload["speed"],
            payload["allowed_vlans"],
            payload["port_security"],
            payload["max_mac"],
            payload["violation_mode"],
            payload["bpdu_guard"],
            payload["type"],
        ))
        row = cur.fetchone()
        conn.commit()
        return jsonify({
            "success": True,
            "message": "Interface creee avec succes",
            "interface": row_to_interface(row),
        }), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()


@interface_bp.route("/api/interface/<int:interface_id>", methods=["PUT"])
def update_interface(interface_id):
    try:
        payload = normalize_interface_payload(request.get_json() or {}, forced_id=interface_id)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            UPDATE interface
            SET nom = %s,
                ip = %s,
                vlan_id = %s,
                equipement_id = %s,
                status = %s,
                mode = %s,
                speed = %s,
                allowed_vlans = %s,
                port_security = %s,
                max_mac = %s,
                violation_mode = %s,
                bpdu_guard = %s,
                type = %s
            WHERE id_interface = %s
            RETURNING id_interface, nom, ip, vlan_id, equipement_id, status, mode,
                      speed, allowed_vlans, port_security, max_mac, violation_mode,
                      bpdu_guard, type
        """, (
            payload["nom"],
            payload["ip"],
            payload["vlan_id"],
            payload["equipement_id"],
            payload["status"],
            payload["mode"],
            payload["speed"],
            payload["allowed_vlans"],
            payload["port_security"],
            payload["max_mac"],
            payload["violation_mode"],
            payload["bpdu_guard"],
            payload["type"],
            interface_id,
        ))
        row = cur.fetchone()
        if not row:
            conn.rollback()
            return jsonify({"success": False, "error": "Interface introuvable"}), 404

        conn.commit()
        return jsonify({
            "success": True,
            "message": f"Interface {interface_id} mise a jour avec succes",
            "interface": row_to_interface(row),
        })
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()


@interface_bp.route("/api/interface/<int:interface_id>", methods=["DELETE"])
def delete_interface(interface_id):
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            DELETE FROM interface
            WHERE id_interface = %s
            RETURNING id_interface, nom, ip, vlan_id, equipement_id, status, mode,
                      speed, allowed_vlans, port_security, max_mac, violation_mode,
                      bpdu_guard, type
        """, (interface_id,))
        row = cur.fetchone()
        if not row:
            conn.rollback()
            return jsonify({"success": False, "error": "Interface introuvable"}), 404

        conn.commit()
        return jsonify({
            "success": True,
            "message": f"Interface {interface_id} supprimee avec succes",
            "interface": row_to_interface(row),
        })
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()
