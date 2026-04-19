from flask import Blueprint, jsonify, request
from Database.db import get_db_connection
import psycopg2.extras  # ← AJOUTÉ : Pour les dictionnaires comme alerts.py
import re

# ─── Blueprint ───
regles_bp = Blueprint("regles", __name__)


# ─── FONCTIONS SQL CORRIGÉES ───

def afficher_db():
    """Récupère toutes les règles de la BDD - Version RealDictCursor"""
    conn = get_db_connection()
    if conn is None:
        return []

    try:
        # ✅ CORRECTION 1 : Utilisation de RealDictCursor comme alerts.py
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT sid, rule FROM regles ORDER BY sid;")
        rows = cur.fetchall()
        return rows  # Retourne des dictionnaires : [{"sid": 1, "rule": "..."}, ...]
    except Exception as e:
        print(f"❌ Erreur lors de la lecture des règles : {e}")
        return []
    finally:
        conn.close()


def ajouter_regle(line):
    """Parse et ajoute une règle Snort à la BDD - Version sécurisée"""
    # ✅ CORRECTION 2 : Validation du format avant parsing
    if not line or not line.strip():
        raise Exception("La règle ne peut pas être vide")
    
    parts = line.split()
    if len(parts) < 7:
        raise Exception(f"Format de règle invalide: {len(parts)} parties trouvées, 7 attendues")
    
    # Vérifier la présence du séparateur '->'
    if parts[4] != '->':
        raise Exception("Le séparateur '->' est manquant ou mal positionné")
    
    conn = get_db_connection()
    if conn is None:
        raise Exception("Connexion à la base de données impossible")

    try:
        # Extraction sécurisée
        action = parts[0]
        protocol = parts[1]
        src_ip = parts[2]
        src_port = parts[3]
        dst_ip = parts[5]
        dst_port = parts[6]

        msg = re.search(r'msg:"(.*?)"', line)
        sid_match = re.search(r'sid:(\d+)', line)

        message = msg.group(1) if msg else ""
        
        # ✅ CORRECTION 3 : Gestion du SID automatique si absent
        if not sid_match:
            # Générer un SID auto-incrémenté
            with conn.cursor() as cursor:
                cursor.execute("SELECT COALESCE(MAX(sid), 1000000) + 1 FROM regles")
                sid = cursor.fetchone()[0]
            # Ajouter le SID à la règle texte
            line = f"{line.rstrip(';')}; sid:{sid};"
        else:
            sid = int(sid_match.group(1))

        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO regles 
                (sid, message, protocol, src_ip, src_port, dst_ip, dst_port, action, rule)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (sid) DO NOTHING
                """,
                (sid, message, protocol, src_ip, src_port, dst_ip, dst_port, action, line)
            )
            conn.commit()
    except Exception as e:
        raise Exception(f"Erreur lors de l'ajout : {e}")
    finally:
        conn.close()


def modifier_regle(first_sid, line):
    """Met à jour une règle existante - Version sécurisée"""
    # ✅ CORRECTION 4 : Validation avant parsing
    if not line or not line.strip():
        raise Exception("La règle ne peut pas être vide")
    
    parts = line.split()
    if len(parts) < 7:
        raise Exception(f"Format de règle invalide: {len(parts)} parties trouvées")
    
    if parts[4] != '->':
        raise Exception("Le séparateur '->' est manquant")
    
    conn = get_db_connection()
    if conn is None:
        raise Exception("Connexion à la base de données impossible")

    try:
        action = parts[0]
        protocol = parts[1]
        src_ip = parts[2]
        src_port = parts[3]
        dst_ip = parts[5]
        dst_port = parts[6]

        msg = re.search(r'msg:"(.*?)"', line)
        message = msg.group(1) if msg else ""

        # Forcer le SID original dans la règle texte
        if f"sid:{first_sid}" not in line:
            line = re.sub(r'sid:\d+', f'sid:{first_sid}', line)

        with conn.cursor() as cursor:
            # Vérifier si l'enregistrement existe
            cursor.execute("SELECT COUNT(*) FROM regles WHERE sid = %s", (first_sid,))
            if cursor.fetchone()[0] == 0:
                # INSERT
                cursor.execute(
                    """
                    INSERT INTO regles (sid, message, protocol, src_ip, src_port, dst_ip, dst_port, action, rule)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (first_sid, message, protocol, src_ip, src_port, dst_ip, dst_port, action, line)
                )
            else:
                # UPDATE
                cursor.execute(
                    """
                    UPDATE regles
                    SET message = %s, protocol = %s, src_ip = %s, src_port = %s, 
                        dst_ip = %s, dst_port = %s, action = %s, rule = %s
                    WHERE sid = %s
                    """,
                    (message, protocol, src_ip, src_port, dst_ip, dst_port, action, line, first_sid)
                )
            conn.commit()
    except Exception as e:
        raise Exception(f"Erreur lors de la modification : {e}")
    finally:
        conn.close()


def supprimer_regle(sid):
    """Supprime une règle par son SID"""
    conn = get_db_connection()
    if conn is None:
        raise Exception("Connexion à la base de données impossible")
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM regles WHERE sid = %s", (sid,))
            conn.commit()
    except Exception as e:
        raise Exception(f"Erreur suppression : {e}")
    finally:
        conn.close()


def reset_db():
    """Vide la table des règles"""
    conn = get_db_connection()
    if conn is None:
        raise Exception("Connexion à la base de données impossible")
    try:
        with conn.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE regles;")
            conn.commit()
    except Exception as e:
        raise Exception(f"Erreur reset : {e}")
    finally:
        conn.close()


# ─── ROUTES API (inchangées mais maintenant avec données cohérentes) ───

@regles_bp.route("/api/regles", methods=["GET"])
def get_regles():
    """Récupère toutes les règles - Format JSON cohérent"""
    try:
        rows = afficher_db()
        regles = [{"sid": row["sid"], "rule": row["rule"]} for row in rows]
        return jsonify({
            "success": True, 
            "count": len(regles), 
            "rules": regles  # ← CHANGÉ : "rules" au lieu de "regles" (cohérence anglais)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@regles_bp.route("/api/regles", methods=["POST"])
def add_regle():
    """Ajoute une nouvelle règle - Avec gestion d'erreur détaillée"""
    data = request.get_json()
    
    if not data or "rule" not in data:
        return jsonify({"success": False, "error": "La règle est requise"}), 400
    
    try:
        ajouter_regle(data["rule"])
        return jsonify({"success": True, "message": "Règle ajoutée avec succès"}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400  # ← 400 pour erreur de format


@regles_bp.route("/api/regles/<int:sid>", methods=["PUT"])
def update_regle(sid):
    """Met à jour une règle existante"""
    data = request.get_json()
    
    if not data or "rule" not in data:
        return jsonify({"success": False, "error": "La règle est requise"}), 400
    
    try:
        modifier_regle(sid, data["rule"])
        return jsonify({"success": True, "message": f"Règle {sid} mise à jour avec succès"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@regles_bp.route("/api/regles/<int:sid>", methods=["DELETE"])
def delete_regle(sid):
    """Supprime une règle"""
    try:
        supprimer_regle(sid)
        return jsonify({"success": True, "message": f"Règle {sid} supprimée avec succès"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@regles_bp.route("/api/regles/reset", methods=["POST"])
def reset_regles():
    """Réinitialise toutes les règles"""
    try:
        reset_db()
        return jsonify({"success": True, "message": "Base de données des règles réinitialisée"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500