from flask import Blueprint, request, jsonify
from utils.security import check_password
from Database.db import get_db_connection

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, password, role FROM users WHERE username = %s", (username,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    
    if user and check_password(password, user[2]):
        return jsonify({
            "message": "login success",
            "user": {"id": user[0], "username": user[1], "role": user[3]}
        }), 200
    
    return jsonify({"error": "Invalid credentials"}), 401