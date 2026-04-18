from flask import Blueprint, request, jsonify
from utils.security import check_password
from Database.db import get_db_connection
from flask_jwt_extended import create_access_token

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Nom d'utilisateur et mot de passe requis"}), 400

    try:
        # Récupération de l'utilisateur depuis la base de données
        conn = get_db_connection()
        cursor = conn.cursor()
        # Requête sur la table 'utilisateur'
        cursor.execute("SELECT id_user, username, password, role FROM utilisateur WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception as e:
        return jsonify({"error": f"Erreur de base de données : {str(e)}"}), 500

    # Vérification de l'existence de l'utilisateur et du mot de passe
    # Si user[2] est une chaîne (VARCHAR), on l'encode en bytes pour bcrypt
    if user and check_password(password, user[2].encode('utf-8') if isinstance(user[2], str) else user[2]):
        # Création du token incluant le rôle de l'utilisateur (additional_claims)
        access_token = create_access_token(identity=username, additional_claims={"role": user[3]})
        
        return jsonify({
            "message": "login success",
            "access_token": access_token,
            "role": user[3]
        }), 200
    else:
        return jsonify({"error": "Identifiants incorrects"}), 401