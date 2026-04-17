from functools import wraps

def require_role(role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # vérifier rôle utilisateur
            return f(*args, **kwargs)
        return wrapper
    return decorator