from flask import Flask, request, jsonify, session
from flask_cors import CORS  # Important pour autoriser ton frontend
from Database.db import get_db_connection, return_db_connection
from utils.security import check_password
import secrets


app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
CORS(app, supports_credentials=True)  # Permet au frontend de communiquer avec backend


# 1. Route login - correspond à ton frontend
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    
    if not username or not password:
        return jsonify({"error": "Username et password requis"}), 400
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, username, password, role FROM users WHERE username = %s",
        (username,)
    )
    user = cur.fetchone()
    cur.close()
    # return connection to pool
    return_db_connection(conn)
    
    if user and check_password(password, user[2]):
        # Récupérer le rôle et le mapper avec les rôles du frontend
        db_role = user[3]  # ex: "superadmin" dans ta BDD
        
        # Mapper ton rôle BDD vers les rôles du frontend
        role_mapping = {
            'superadmin': 'ADMIN',
            'admin': 'NETWORK_ADMIN',
            'security': 'SECURITY_ADMIN',
            'auditor': 'AUDITOR'
        }
        
        frontend_role = role_mapping.get(db_role, 'AUDITOR')
        
        # Retourner le format attendu par auth.js
        return jsonify({
            "success": True,
            "role": frontend_role,
            "name": username,
            "username": username,
            "message": "Login réussi"
        }), 200
    
    return jsonify({"error": "Identifiants incorrects"}), 401

# 2. Route logout
@app.route("/api/logout", methods=["POST"])
def logout():
    return jsonify({"success": True, "message": "Déconnecté"}), 200

# 3. Route pour vérifier la session (optionnel)
@app.route("/api/check-session", methods=["GET"])
def check_session():
    # Le frontend gère déjà la session avec localStorage
    # Mais tu peux ajouter une vérification supplémentaire
    return jsonify({"status": "ok"}), 200

# 4. Route pour récupérer les utilisateurs (API protégée)
@app.route("/api/users", methods=["GET"])
def get_users():
    # Vérifier le token/rôle depuis le header
    role = request.headers.get('X-User-Role')
    
    if role != 'ADMIN':
        return jsonify({"error": "Accès non autorisé"}), 403
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, email, role FROM users")
    users = cur.fetchall()
    cur.close()
    return_db_connection(conn)
    
    users_list = [{"id": u[0], "username": u[1], "email": u[2], "role": u[3]} for u in users]
    return jsonify({"users": users_list}), 200

# 5. Route pour créer un utilisateur (API protégée)
@app.route("/api/users", methods=["POST"])
def create_user():
    role = request.headers.get('X-User-Role')
    
    if role != 'ADMIN':
        return jsonify({"error": "Seul l'admin peut créer des utilisateurs"}), 403
    
    data = request.json
    # Code pour créer l'utilisateur...
    
    return jsonify({"success": True, "message": "Utilisateur créé"}), 201

if __name__ == "__main__":
    app.run(debug=True, port=5000)