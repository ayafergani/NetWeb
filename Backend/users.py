from flask import Blueprint, request, jsonify
from Database.db import get_db_connection
from utils.decorators import require_role
from utils.security import hash_password
import psycopg2

# Création du Blueprint pour les utilisateurs
users_bp = Blueprint('users', __name__)

class User:
    def __init__(self, id, username, email, password, role):
        self.id = id
        self.username = username
        self.email = email
        self.password = password
        self.role = role

@users_bp.route("/users", methods=["POST"])
@require_role("ADMIN")  # Seul un ADMIN peut créer d'autres utilisateurs
def create_user():
    data = request.json
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role")

    if not all([username, email, password, role]):
        return jsonify({"error": "Données incomplètes"}), 400

    hashed_pw = hash_password(password).decode('utf-8')

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO utilisateur (username, email, password, role) VALUES (%s, %s, %s, %s) RETURNING id_user;",
            (username, email, hashed_pw, role)
        )
        new_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Utilisateur créé", "id": new_id}), 201
    except psycopg2.IntegrityError:
        return jsonify({"error": "Cet utilisateur ou cet email existe déjà"}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@users_bp.route("/users", methods=["GET"])
@require_role("ADMIN")
def get_users():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id_user, username, email, role FROM utilisateur;")
        users = [{"id": row[0], "username": row[1], "email": row[2], "role": row[3]} for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return jsonify({"users": users}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@users_bp.route("/users/<int:user_id>", methods=["DELETE"])
@require_role("ADMIN")
def delete_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM utilisateur WHERE id_user = %s;", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Utilisateur supprimé"}), 200