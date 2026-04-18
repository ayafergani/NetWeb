from flask import Blueprint, request, jsonify
from utils.security import check_password, hash_password
from Database.db import get_db_connection
from flask_jwt_extended import create_access_token, decode_token
from datetime import timedelta

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Nom d'utilisateur et mot de passe requis"}), 400

    try:
        # Nettoyer les entrées
        username = username.strip()
        password = password.strip()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        # Utiliser LOWER() pour une recherche insensible à la casse
        cursor.execute("SELECT id_user, username, password, role FROM utilisateur WHERE LOWER(username) = LOWER(%s)", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception as e:
        return jsonify({"error": f"Erreur de base de données : {str(e)}"}), 500

    if not user:
        return jsonify({"error": "Identifiants incorrects"}), 401
    
    # Récupérer le hash stocké
    stored_hash = user[2]
    
    # Conversion systématique en bytes pour bcrypt
    if isinstance(stored_hash, str):
        stored_hash = stored_hash.encode('utf-8')
    elif not isinstance(stored_hash, bytes):
        return jsonify({"error": "Format de mot de passe invalide"}), 500
    
    # Vérification du mot de passe
    if check_password(password, stored_hash):
        # Création du token
        access_token = create_access_token(identity=username, additional_claims={"role": user[3]})
        
        return jsonify({
            "message": "login success",
            "access_token": access_token,
            "role": user[3]
        }), 200
    else:
        return jsonify({"error": "Identifiants incorrects"}), 401


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.json
    email = data.get("email")

    if not email:
        return jsonify({"error": "Email requis"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id_user, username FROM utilisateur WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception as e:
        return jsonify({"error": f"Erreur de base de données : {str(e)}"}), 500

    if user:
        username = user[1]
        # token short-lived (30 minutes) with a pw_reset claim
        token = create_access_token(identity=username, additional_claims={"pw_reset": True}, expires_delta=timedelta(minutes=30))
        reset_link = f"http://localhost:5500/reset-password.html?token={token}"
        print(f"[INFO] Envoi simulé de l'email de réinitialisation à {email}: {reset_link}")

    return jsonify({"message": "Si un compte existe pour cet email, un lien de réinitialisation a été envoyé."}), 200


@auth_bp.route('/api/check-email', methods=['POST'])
def check_email():
    data = request.json
    identity = (data.get('identity') or '').strip()
    if not identity:
        return jsonify({'error': 'identity requis'}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id_user, username, email FROM utilisateur WHERE LOWER(email) = LOWER(%s) OR LOWER(username) = LOWER(%s)", (identity, identity))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception as e:
        return jsonify({'error': f'Erreur base de données: {str(e)}'}), 500

    if not user:
        return jsonify({'error': 'Utilisateur non trouvé'}), 404

    return jsonify({'id': user[0], 'username': user[1], 'email': user[2]}), 200


@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    """
    Réinitialise le mot de passe en utilisant un token JWT
    AUCUNE CONTRAINTE DE TAILLE sur le mot de passe
    """
    data = request.json
    token = data.get("token")
    new_password = data.get("new_password")

    if not token or not new_password:
        return jsonify({"error": "Token et nouveau mot de passe requis"}), 400

    # Nettoyer le mot de passe (mais sans contrainte de taille)
    new_password = new_password.strip()

    try:
        decoded = decode_token(token)
    except Exception as e:
        return jsonify({"error": "Token invalide ou expiré"}), 400

    # Vérifier la présence de la claim pw_reset
    if not decoded.get("pw_reset"):
        return jsonify({"error": "Token invalide pour la réinitialisation"}), 400

    username = decoded.get("sub")
    if not username:
        return jsonify({"error": "Token invalide"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Hachage (bcrypt génère des bytes)
        new_hash_bytes = hash_password(new_password)
        
        # 2. Conversion en string pour stockage VARCHAR/TEXT
        new_hash_str = new_hash_bytes.decode('utf-8')
        
        # 3. Update de la base de données
        cursor.execute("UPDATE utilisateur SET password = %s WHERE username = %s", (new_hash_str, username))
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "Utilisateur non trouvé"}), 404
            
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "message": "Mot de passe réinitialisé avec succès. Vous pouvez maintenant vous connecter avec votre nouveau mot de passe."
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Erreur de base de données : {str(e)}"}), 500


@auth_bp.route('/reset-password-final', methods=['POST'])
def reset_password_final():
    """
    Route alternative pour réinitialiser le mot de passe sans token
    AUCUNE CONTRAINTE DE TAILLE sur le mot de passe
    """
    data = request.json
    username = data.get('username')
    new_password = data.get('new_password')

    if not username or not new_password:
        return jsonify({'error': 'username et new_password requis'}), 400

    # Nettoyer les entrées (mais sans contrainte de taille)
    username = username.strip()
    new_password = new_password.strip()

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Hachage (bcrypt génère des bytes)
        new_hash_bytes = hash_password(new_password)
        
        # 2. Conversion en string pour stockage VARCHAR/TEXT
        new_hash_str = new_hash_bytes.decode('utf-8')
        
        # 3. Update de la base de données
        cursor.execute("UPDATE utilisateur SET password = %s WHERE username = %s", (new_hash_str, username))
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Utilisateur introuvable'}), 404
            
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'message': 'Mot de passe mis à jour avec succès. Veuillez vous reconnecter avec votre nouveau mot de passe.'
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur base de données: {str(e)}'}), 500


# Route de vérification pour déboguer
@auth_bp.route("/verify-password-storage", methods=["POST"])
def verify_password_storage():
    """
    Vérifie comment le mot de passe est stocké en base de données
    """
    data = request.json
    username = data.get("username")
    
    if not username:
        return jsonify({"error": "username requis"}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT username, LENGTH(password) as pwd_length, LEFT(password, 10) as pwd_start FROM utilisateur WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not user:
            return jsonify({"error": "Utilisateur non trouvé"}), 404
        
        return jsonify({
            "username": user[0],
            "password_length": user[1],
            "password_start": user[2],
            "expected_bcrypt_length": 60,
            "is_valid_length": user[1] == 60
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500