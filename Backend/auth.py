from flask import Blueprint, request, jsonify
from utils.security import check_password, hash_password
from Database.db import get_db_connection
from flask_jwt_extended import create_access_token, decode_token, jwt_required, get_jwt_identity
from datetime import timedelta
import datetime

auth_bp = Blueprint('auth', __name__)

# ✅ Fonction pour ajouter des logs
def add_log(username, action, status='success', ip_address=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO logs (username, action, status, ip_address) 
            VALUES (%s, %s, %s, %s)
        """, (username, action, status, ip_address))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erreur ajout log: {e}")

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    ip_address = request.remote_addr or request.headers.get('X-Forwarded-For', 'unknown')

    if not username or not password:
        add_log(username or 'unknown', 'login_failed', 'error', ip_address)
        return jsonify({"error": "Nom d'utilisateur et mot de passe requis"}), 400

    try:
        username = username.strip()
        password = password.strip()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id_user, username, password, role, email FROM utilisateur WHERE LOWER(username) = LOWER(%s)", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception as e:
        add_log(username, 'login_error', 'error', ip_address)
        return jsonify({"error": f"Erreur de base de données : {str(e)}"}), 500

    if not user:
        add_log(username, 'login_failed', 'error', ip_address)
        return jsonify({"error": "Identifiants incorrects"}), 401
    
    stored_hash = user[2]
    
    if isinstance(stored_hash, str):
        stored_hash = stored_hash.encode('utf-8')
    elif not isinstance(stored_hash, bytes):
        return jsonify({"error": "Format de mot de passe invalide"}), 500
    
    if check_password(password, stored_hash):
        # ✅ Log du succès
        add_log(username, 'login', 'success', ip_address)
        
        # ✅ Mettre à jour last_login
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE utilisateur SET last_login = NOW() WHERE id_user = %s",
                (user[0],)
            )
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Erreur mise à jour last_login: {e}")
        
        user_role = user[3].upper() if user[3] else "AUDITOR"
        access_token = create_access_token(identity=user[1], additional_claims={"role": user_role})
        
        return jsonify({
            "message": "login success",
            "access_token": access_token,
            "username": user[1],
            "email": user[4] or "",
            "role": user_role
        }), 200
    else:
        add_log(username, 'login_failed', 'error', ip_address)
        return jsonify({"error": "Identifiants incorrects"}), 401

# ✅ ROUTE DE DÉCONNEXION
@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    try:
        current_user = get_jwt_identity()
        ip_address = request.remote_addr or request.headers.get('X-Forwarded-For', 'unknown')
        
        # ✅ Log du logout
        add_log(current_user, 'logout', 'success', ip_address)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE utilisateur SET last_logout = NOW() WHERE username = %s",
            (current_user,)
        )
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({"success": True, "message": "Déconnexion réussie"}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ✅ Route pour récupérer les logs
@auth_bp.route("/api/logs", methods=["GET"])
@jwt_required()
def get_logs():
    try:
        current_user = get_jwt_identity()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT username, action, status, timestamp, ip_address 
            FROM logs 
            ORDER BY timestamp DESC 
            LIMIT 50
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        logs = []
        for row in rows:
            logs.append({
                "username": row[0],
                "action": row[1],
                "status": row[2],
                "timestamp": row[3].isoformat() if row[3] else None,
                "ip_address": row[4]
            })
        
        return jsonify({"success": True, "logs": logs}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

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
    data = request.json
    token = data.get("token")
    new_password = data.get("new_password")

    if not token or not new_password:
        return jsonify({"error": "Token et nouveau mot de passe requis"}), 400

    new_password = new_password.strip()

    try:
        decoded = decode_token(token)
    except Exception as e:
        return jsonify({"error": "Token invalide ou expiré"}), 400

    if not decoded.get("pw_reset"):
        return jsonify({"error": "Token invalide pour la réinitialisation"}), 400

    username = decoded.get("sub")
    if not username:
        return jsonify({"error": "Token invalide"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        new_hash_bytes = hash_password(new_password)
        new_hash_str = new_hash_bytes.decode('utf-8')
        
        cursor.execute("UPDATE utilisateur SET password = %s WHERE username = %s", (new_hash_str, username))
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"error": "Utilisateur non trouvé"}), 404
            
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "message": "Mot de passe réinitialisé avec succès."
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Erreur de base de données : {str(e)}"}), 500

@auth_bp.route('/reset-password-final', methods=['POST'])
def reset_password_final():
    data = request.json
    username = data.get('username')
    new_password = data.get('new_password')

    if not username or not new_password:
        return jsonify({'error': 'username et new_password requis'}), 400

    username = username.strip()
    new_password = new_password.strip()

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        new_hash_bytes = hash_password(new_password)
        new_hash_str = new_hash_bytes.decode('utf-8')
        
        cursor.execute("UPDATE utilisateur SET password = %s WHERE username = %s", (new_hash_str, username))
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Utilisateur introuvable'}), 404
            
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'message': 'Mot de passe mis à jour avec succès.'
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erreur base de données: {str(e)}'}), 500

@auth_bp.route("/verify-password-storage", methods=["POST"])
def verify_password_storage():
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