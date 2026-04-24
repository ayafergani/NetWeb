from flask import Blueprint, jsonify, request
from Database.db import get_db_connection
import ipaddress
import psycopg2.extras

vlan_bp = Blueprint("vlan", __name__)


def get_vlan_columns(conn):
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'vlan'
        """)
        return {row[0] for row in cur.fetchall()}
    finally:
        cur.close()


def derive_network_from_gateway(gateway):
    if not gateway:
        return ""

    try:
        return str(ipaddress.ip_network(f"{gateway}/24", strict=False))
    except ValueError:
        return ""


def build_vlan_response(row):
    gateway = row.get("gateway") or ""
    return {
        "id_vlan": row.get("id_vlan"),
        "id": row.get("id_vlan"),
        "nom": row.get("nom"),
        "name": row.get("nom"),
        "reseau": row.get("reseau") or "",
        "gateway": gateway,
        "vlanIp": gateway or "--",
        "type": row.get("type") or "Data",
        "ports": row.get("ports") or "",
        "status": row.get("status") or "Active",
        "switchName": row.get("switch_name") or "",
        "switchIp": row.get("switch_ip") or "",
        "devices": 0,
    }


def normalize_vlan_payload(data, forced_vlan_id=None):
    if not isinstance(data, dict):
        raise ValueError("Le corps JSON est invalide")

    raw_id = forced_vlan_id if forced_vlan_id is not None else data.get("id_vlan", data.get("id", data.get("vlan_id")))
    try:
        id_vlan = int(raw_id)
    except (TypeError, ValueError):
        raise ValueError("id_vlan doit etre un entier")

    gateway = str(data.get("gateway", data.get("vlanIp", data.get("vlan_ip", "")))).strip()
    reseau = str(data.get("reseau", "")).strip()
    if not reseau and gateway:
        reseau = derive_network_from_gateway(gateway)

    payload = {
        "id_vlan": id_vlan,
        "nom": str(data.get("nom", data.get("name", data.get("vlan_name", "")))).strip(),
        "reseau": reseau,
        "gateway": gateway,
        "type": str(data.get("type", "Data")).strip() or "Data",
        "ports": str(data.get("ports", "")).strip(),
        "status": str(data.get("status", "Active")).strip() or "Active",
        "switch_name": str(data.get("switchName", data.get("switch_name", ""))).strip(),
        "switch_ip": str(data.get("switchIp", data.get("switch_ip", ""))).strip(),
        "switch_user": str(data.get("switchUser", data.get("switch_user", ""))).strip(),
        "switch_pass": str(data.get("switchPass", data.get("switch_password", ""))).strip(),
    }

    if not payload["nom"]:
        raise ValueError("Le nom du VLAN est requis")
    if not payload["switch_name"]:
        raise ValueError("Le nom du switch est requis")
    if not payload["switch_ip"]:
        raise ValueError("L'IP du switch est requise")
    if not payload["switch_user"]:
        raise ValueError("L'utilisateur SSH est requis")
    if not payload["switch_pass"]:
        raise ValueError("Le mot de passe SSH est requis")

    if payload["gateway"]:
        try:
            ipaddress.ip_address(payload["gateway"])
        except ValueError:
            raise ValueError("gateway doit etre une adresse IP valide")

    if payload["reseau"]:
        try:
            ipaddress.ip_network(payload["reseau"], strict=False)
        except ValueError:
            raise ValueError("reseau doit etre au format CIDR, ex: 192.168.10.0/24")

    return payload


def get_returning_fields(columns):
    fields = [
        "id_vlan",
        "nom",
        "reseau",
        "gateway",
        "type",
        "ports",
        "status",
    ]

    if "switch_name" in columns:
        fields.append("switch_name")
    else:
        fields.append("NULL AS switch_name")

    if "switch_ip" in columns:
        fields.append("switch_ip")
    else:
        fields.append("NULL AS switch_ip")

    return fields


@vlan_bp.route("/api/vlan", methods=["GET"])
@vlan_bp.route("/vlan", methods=["GET"])
def get_vlans():
    conn = get_db_connection()
    try:
        columns = get_vlan_columns(conn)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(f"""
            SELECT {", ".join(get_returning_fields(columns))}
            FROM vlan
            ORDER BY id_vlan ASC
        """)
        rows = cur.fetchall()
        vlans = [build_vlan_response(row) for row in rows]
        return jsonify({"success": True, "count": len(vlans), "vlans": vlans})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()


@vlan_bp.route("/api/vlan", methods=["POST"])
@vlan_bp.route("/vlan", methods=["POST"])
@vlan_bp.route("/api/network/deploy-vlan", methods=["POST"])
def create_vlan():
    try:
        payload = normalize_vlan_payload(request.get_json())
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

    conn = get_db_connection()
    try:
        columns = get_vlan_columns(conn)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT 1 FROM vlan WHERE id_vlan = %s", (payload["id_vlan"],))
        if cur.fetchone():
            return jsonify({"success": False, "error": f"Le VLAN {payload['id_vlan']} existe deja"}), 409

        insert_columns = ["id_vlan", "nom", "reseau", "gateway", "type", "ports", "status"]
        insert_values = [
            payload["id_vlan"],
            payload["nom"],
            payload["reseau"] or None,
            payload["gateway"] or None,
            payload["type"],
            payload["ports"],
            payload["status"],
        ]

        if "switch_name" in columns:
            insert_columns.append("switch_name")
            insert_values.append(payload["switch_name"])

        if "switch_ip" in columns:
            insert_columns.append("switch_ip")
            insert_values.append(payload["switch_ip"])

        placeholders = ", ".join(["%s"] * len(insert_columns))
        cur.execute(f"""
            INSERT INTO vlan ({", ".join(insert_columns)})
            VALUES ({placeholders})
            RETURNING {", ".join(get_returning_fields(columns))}
        """, insert_values)
        row = cur.fetchone()
        conn.commit()
        return jsonify({
            "success": True,
            "message": "VLAN cree avec succes",
            "vlan": build_vlan_response(row),
        }), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()


@vlan_bp.route("/api/vlan/<int:id_vlan>", methods=["PUT"])
@vlan_bp.route("/vlan/<int:id_vlan>", methods=["PUT"])
def update_vlan(id_vlan):
    try:
        payload = normalize_vlan_payload(request.get_json() or {}, forced_vlan_id=id_vlan)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

    conn = get_db_connection()
    try:
        columns = get_vlan_columns(conn)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        set_clauses = [
            "nom = %s",
            "reseau = %s",
            "gateway = %s",
            "type = %s",
            "ports = %s",
            "status = %s",
        ]
        values = [
            payload["nom"],
            payload["reseau"] or None,
            payload["gateway"] or None,
            payload["type"],
            payload["ports"],
            payload["status"],
        ]

        if "switch_name" in columns:
            set_clauses.append("switch_name = %s")
            values.append(payload["switch_name"])

        if "switch_ip" in columns:
            set_clauses.append("switch_ip = %s")
            values.append(payload["switch_ip"])

        values.append(id_vlan)

        cur.execute(f"""
            UPDATE vlan
            SET {", ".join(set_clauses)}
            WHERE id_vlan = %s
            RETURNING {", ".join(get_returning_fields(columns))}
        """, values)
        row = cur.fetchone()
        if not row:
            conn.rollback()
            return jsonify({"success": False, "error": "VLAN introuvable"}), 404

        conn.commit()
        return jsonify({
            "success": True,
            "message": f"VLAN {id_vlan} mis a jour avec succes",
            "vlan": build_vlan_response(row),
        })
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()


@vlan_bp.route("/api/vlan/<int:id_vlan>", methods=["DELETE"])
@vlan_bp.route("/vlan/<int:id_vlan>", methods=["DELETE"])
def delete_vlan(id_vlan):
    conn = get_db_connection()
    try:
        columns = get_vlan_columns(conn)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(f"""
            DELETE FROM vlan
            WHERE id_vlan = %s
            RETURNING {", ".join(get_returning_fields(columns))}
        """, (id_vlan,))
        row = cur.fetchone()
        if not row:
            conn.rollback()
            return jsonify({"success": False, "error": "VLAN introuvable"}), 404

        conn.commit()
        return jsonify({
            "success": True,
            "message": f"VLAN {id_vlan} supprime avec succes",
            "vlan": build_vlan_response(row),
        })
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()
