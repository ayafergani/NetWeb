from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt

def require_role(required_role):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                # Vérifier le JWT
                verify_jwt_in_request()
                
                # Récupérer les claims (dont le rôle)
                claims = get_jwt()
                user_role = claims.get("role", "")
                
                # Alternative : récupérer depuis l'identity si nécessaire
                if not user_role:
                    identity = get_jwt_identity()
                    # Vous pouvez aussi chercher le rôle en DB si besoin
                
                print(f"🔍 Rôle requis: {required_role}, Rôle utilisateur: {user_role}")  # Debug
                
                if user_role != required_role:
                    return jsonify({"error": f"Permission refusée. Rôle {required_role} requis."}), 403
                    
                return fn(*args, **kwargs)
            except Exception as e:
                print(f"❌ Erreur require_role: {e}")
                return jsonify({"error": "Token invalide ou expiré"}), 401
        return wrapper
    return decorator