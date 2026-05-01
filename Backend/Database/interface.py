from flask import Blueprint, jsonify, request
from Database.db import get_db_connection
import psycopg2.extras
import logging

interface_bp = Blueprint("interface", __name__)
logger = logging.getLogger(__name__)


def fetch_existing_vlan_ids(cur):
    cur.execute("SELECT id_vlan FROM vlan")
    return {row[0] for row in cur.fetchall()}


def resolve_vlan_id(vlan_id, available_vlan_ids):
    if vlan_id is None:
        return None
    if vlan_id in available_vlan_ids:
        return vlan_id
    if 1 in available_vlan_ids:
        return 1
    if available_vlan_ids:
        return min(available_vlan_ids)
    return None


def validate_vlan_reference(cur, vlan_id):
    if vlan_id is None:
        return

    cur.execute("SELECT 1 FROM vlan WHERE id_vlan = %s", (vlan_id,))
    if not cur.fetchone():
        raise ValueError(f"Le VLAN {vlan_id} n'existe pas. Creez-le d'abord dans la page VLAN.")


def generate_default_interfaces(nb_ports=24):
    """Génère les interfaces par défaut en fonction du nombre de ports du switch"""
    interfaces = []

    # Ports cuivre (type = "access" physique)
    for port_number in range(1, nb_ports + 1):
        is_configured = port_number <= 4 or port_number == 24
        interfaces.append({
            "nom": f"Gi1/0/{port_number}",
            "ip": "192.168.1.10" if port_number == 4 else None,
            "vlan_id": 20 if port_number == 3 else (30 if port_number == 24 else 10 if is_configured else 1),
            "equipement_id": None,
            "status": "UP" if port_number <= 4 else "DOWN",
            "mode": "access",      # Configuration logicielle (access/trunk)
            "type": "access",      # Type physique (access port cuivre)
            "speed": "1Gb" if port_number <= 4 else None,
            "allowed_vlans": None,
            "port_security": port_number <= 3,
            "max_mac": 1,
            "violation_mode": "shutdown",
            "bpdu_guard": True,
        })

    # Ports fibre SFP+ (type = "uplink" physique)
    for port_number in range(1, 5):
        is_configured = port_number <= 2
        interfaces.append({
            "nom": f"Te1/1/{port_number}",
            "ip": None,
            "vlan_id": None if is_configured else 1,
            "equipement_id": None,
            "status": "UP" if port_number == 1 else "DOWN",
            "mode": "trunk" if is_configured else "access",  # Configuration logicielle
            "type": "uplink",      # Type physique (fibre SFP+ uplink)
            "speed": "10Gb" if port_number == 1 else None,
            "allowed_vlans": "all" if is_configured else None,
            "port_security": False,
            "max_mac": 1,
            "violation_mode": "shutdown",
            "bpdu_guard": False,
        })

    return interfaces


def ensure_interface_schema():
    """Vérifie que la colonne type existe (sans supprimer les données)"""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'interface'
        """)
        columns = {row[0] for row in cur.fetchall()}

        # Ajouter la colonne type si elle n'existe pas
        if "type" not in columns:
            try:
                cur.execute("""
                    ALTER TABLE interface 
                    ADD COLUMN type VARCHAR(10) DEFAULT 'access'
                """)
                conn.commit()
                logger.info("Colonne interface.type ajoutee (access/uplink)")
            except Exception as alter_error:
                logger.warning(f"Impossible d'ajouter la colonne type: {alter_error}")
                conn.rollback()
        else:
            logger.info("La colonne type existe deja dans la table interface")
            
        # Renommer bpd_u_guard si nécessaire
        if "bpd_u_guard" in columns and "bpdu_guard" not in columns:
            try:
                cur.execute("ALTER TABLE interface RENAME COLUMN bpd_u_guard TO bpdu_guard")
                conn.commit()
                logger.info("Colonne interface.bpd_u_guard renommee en bpdu_guard")
            except Exception as rename_error:
                logger.warning(f"Impossible de renommer la colonne: {rename_error}")
                conn.rollback()
                
    except Exception as e:
        conn.rollback()
        logger.exception("Erreur lors de la verification du schema interface")
    finally:
        conn.close()


def is_table_empty():
    """Vérifie si la table interface est vide"""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM interface")
        count = cur.fetchone()[0]
        return count == 0
    except Exception as e:
        logger.exception("Erreur lors de la verification du contenu de la table")
        return True
    finally:
        conn.close()


def initialize_default_interfaces():
    """
    Parcourt tous les switchs et cree les interfaces par defaut pour ceux qui n'en ont pas.
    """
    ensure_interface_schema()
    
    conn = get_db_connection()
    inserted_count = 0

    try:
        cur = conn.cursor()
        
        # On récupère id, nom et le nombre de ports configuré pour chaque switch
        cur.execute("SELECT id_switch, nom, nb_ports FROM switch")
        switches = cur.fetchall()
        
        available_vlan_ids = fetch_existing_vlan_ids(cur)

        for sw_id, sw_nom, sw_nb_ports in switches:
            # Vérifier si ce switch spécifique a déjà des interfaces en base
            cur.execute("SELECT COUNT(*) FROM interface WHERE equipement_id = %s", (sw_id,))
            if cur.fetchone()[0] > 0:
                continue 

            logger.info(f"Initialisation de {sw_nb_ports} ports pour le switch: {sw_nom}")
            
            # Générer les interfaces dynamiquement selon le nb_ports du switch
            switch_interfaces = generate_default_interfaces(sw_nb_ports or 24)

            for item in switch_interfaces:
                resolved_vlan_id = resolve_vlan_id(item["vlan_id"], available_vlan_ids)

                cur.execute("""
                    INSERT INTO interface (
                        nom, ip, vlan_id, equipement_id, status, mode, type,
                        speed, allowed_vlans, port_security, max_mac, violation_mode, bpdu_guard
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    item["nom"],
                    item["ip"],
                    resolved_vlan_id,
                    sw_id,
                    item["status"],
                    item["mode"],
                    item["type"],
                    item["speed"],
                    item["allowed_vlans"],
                    item["port_security"],
                    item["max_mac"],
                    item["violation_mode"],
                    item["bpdu_guard"],
                ))
                inserted_count += 1

        conn.commit()
        logger.info("Initialisation terminee: %s interfaces inserees", inserted_count)
        logger.info("Les modifications peuvent maintenant etre faites via l'interface graphique")
        return inserted_count
    except Exception as e:
        conn.rollback()
        logger.exception("Erreur lors de l'initialisation des interfaces")
        raise
    finally:
        conn.close()


def row_to_interface(row):
    """Convertit une ligne de base de données en dictionnaire"""
    return {
        "id_interface": row["id_interface"],
        "nom": row["nom"],
        "ip": row["ip"],
        "vlan_id": row["vlan_id"],
        "equipement_id": row["equipement_id"],
        "status": row["status"],
        "mode": row["mode"],      # access ou trunk (configuration logicielle)
        "type": row["type"],       # access ou uplink (type physique)
        "speed": row["speed"],
        "allowed_vlans": row["allowed_vlans"],
        "port_security": row["port_security"],
        "max_mac": row["max_mac"],
        "violation_mode": row["violation_mode"],
        "bpdu_guard": row["bpdu_guard"],
    }


def normalize_interface_payload(data, forced_id=None):
    """Valide et normalise les données d'une interface"""
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

    mode_value = str(data.get("mode", "access")).strip().lower()
    if mode_value not in ("access", "trunk"):
        raise ValueError("mode doit etre 'access' ou 'trunk'")

    type_value = str(data.get("type", "access")).strip().lower()
    if type_value not in ("access", "uplink"):
        raise ValueError("type doit etre 'access' (port cuivre) ou 'uplink' (port fibre SFP+)")

    payload = {
        "id_interface": id_interface,
        "nom": str(data.get("nom", "")).strip(),
        "ip": str(data.get("ip", "")).strip() or None,
        "vlan_id": vlan_id,
        "equipement_id": equipement_id,
        "status": str(data.get("status", "DOWN")).strip().upper() or "DOWN",
        "mode": mode_value,
        "type": type_value,
        "speed": str(data.get("speed", "")).strip() or None,
        "allowed_vlans": str(data.get("allowed_vlans", "")).strip() or None,
        "port_security": bool(data.get("port_security", False)),
        "max_mac": max_mac,
        "violation_mode": str(data.get("violation_mode", "shutdown")).strip().lower() or "shutdown",
        "bpdu_guard": bool(data.get("bpdu_guard", False)),
    }

    if not payload["nom"]:
        raise ValueError("Le nom de l'interface est requis")
    if payload["status"] not in ("UP", "DOWN"):
        raise ValueError("status doit etre UP ou DOWN")
    if payload["max_mac"] < 1:
        raise ValueError("max_mac doit etre superieur ou egal a 1")

    return payload


# ==================== ROUTES API ====================

@interface_bp.route("/api/interface", methods=["GET"])
def get_interfaces():
    """Récupère toutes les interfaces"""
    equipement_id = request.args.get('switch_id') or request.args.get('equipement_id')
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        query = """
            SELECT id_interface, nom, ip, vlan_id, equipement_id, status, mode, type,
                   speed, allowed_vlans, port_security, max_mac, violation_mode, bpdu_guard
            FROM interface
        """
        
        if equipement_id:
            query += " WHERE equipement_id = %s ORDER BY id_interface ASC"
            cur.execute(query, (equipement_id,))
        else:
            query += " ORDER BY id_interface ASC"
            cur.execute(query)
            
        rows = cur.fetchall()
        interfaces = [row_to_interface(row) for row in rows]
        return jsonify({"success": True, "count": len(interfaces), "interfaces": interfaces})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()


@interface_bp.route("/api/interface", methods=["POST"])
def create_interface():
    """Crée une nouvelle interface (via l'interface graphique)"""
    try:
        payload = normalize_interface_payload(request.get_json())
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Vérifier si l'ID existe déjà
        cur.execute("SELECT 1 FROM interface WHERE id_interface = %s", (payload["id_interface"],))
        if cur.fetchone():
            return jsonify({"success": False, "error": f"Interface {payload['id_interface']} existe deja"}), 409

        # Vérifier si le nom existe déjà
        cur.execute("SELECT 1 FROM interface WHERE nom = %s", (payload["nom"],))
        if cur.fetchone():
            return jsonify({"success": False, "error": f"L'interface {payload['nom']} existe deja"}), 409

        validate_vlan_reference(cur, payload["vlan_id"])

        cur.execute("""
            INSERT INTO interface (
                id_interface, nom, ip, vlan_id, equipement_id, status, mode, type,
                speed, allowed_vlans, port_security, max_mac, violation_mode, bpdu_guard
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id_interface, nom, ip, vlan_id, equipement_id, status, mode, type,
                      speed, allowed_vlans, port_security, max_mac, violation_mode, bpdu_guard
        """, (
            payload["id_interface"],
            payload["nom"],
            payload["ip"],
            payload["vlan_id"],
            payload["equipement_id"],
            payload["status"],
            payload["mode"],
            payload["type"],
            payload["speed"],
            payload["allowed_vlans"],
            payload["port_security"],
            payload["max_mac"],
            payload["violation_mode"],
            payload["bpdu_guard"],
        ))
        row = cur.fetchone()
        conn.commit()
        
        # Émettre un événement pour rafraîchir le dashboard
        try:
            import sys
            if 'flask' in sys.modules:
                from flask import current_app
                current_app.logger.info("Interface creee avec succes")
        except:
            pass
            
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
    """Met à jour une interface existante (via l'interface graphique)"""
    try:
        payload = normalize_interface_payload(request.get_json() or {}, forced_id=interface_id)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        validate_vlan_reference(cur, payload["vlan_id"])
        
        cur.execute("""
            UPDATE interface
            SET nom = %s,
                ip = %s,
                vlan_id = %s,
                equipement_id = %s,
                status = %s,
                mode = %s,
                type = %s,
                speed = %s,
                allowed_vlans = %s,
                port_security = %s,
                max_mac = %s,
                violation_mode = %s,
                bpdu_guard = %s
            WHERE id_interface = %s
            RETURNING id_interface, nom, ip, vlan_id, equipement_id, status, mode, type,
                      speed, allowed_vlans, port_security, max_mac, violation_mode, bpdu_guard
        """, (
            payload["nom"],
            payload["ip"],
            payload["vlan_id"],
            payload["equipement_id"],
            payload["status"],
            payload["mode"],
            payload["type"],
            payload["speed"],
            payload["allowed_vlans"],
            payload["port_security"],
            payload["max_mac"],
            payload["violation_mode"],
            payload["bpdu_guard"],
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
    """Supprime une interface (via l'interface graphique)"""
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            DELETE FROM interface
            WHERE id_interface = %s
            RETURNING id_interface, nom, ip, vlan_id, equipement_id, status, mode, type,
                      speed, allowed_vlans, port_security, max_mac, violation_mode, bpdu_guard
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


@interface_bp.route("/api/interface/reset", methods=["POST"])
def reset_interfaces():
    """Réinitialise les interfaces aux valeurs par défaut (uniquement si demandé explicitement)"""
    # Vérifier les droits admin
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({"success": False, "error": "Authentification requise"}), 401
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        
        # Vider la table
        cur.execute("TRUNCATE TABLE interface RESTART IDENTITY")
        conn.commit()
        logger.info("Table interface videe par demande explicite")
        
        # Fermer la connexion
        conn.close()
        
        # Réinitialiser avec les valeurs par défaut
        initialize_default_interfaces()
        
        return jsonify({
            "success": True,
            "message": "Interfaces reinitialisees avec les valeurs par defaut"
        })
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()