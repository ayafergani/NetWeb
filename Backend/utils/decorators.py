from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import verify_jwt_in_request, get_jwt

def require_role(role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Vérifie qu'un token JWT valide est présent dans la requête
            verify_jwt_in_request()
            
            claims = get_jwt()
            if claims.get("role") != role:
                return jsonify({"error": "Accès non autorisé : privilèges insuffisants"}), 403
                    
            return f(*args, **kwargs)
        return wrapper
    return decorator