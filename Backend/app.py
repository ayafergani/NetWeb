from flask import Flask
from flask_jwt_extended import JWTManager
from users import users_bp
from auth import auth_bp
from Database.alerts import alerts_bp
import os
from flask_cors import CORS

app = Flask(__name__)

# Autoriser les requêtes CORS provenant du frontend
CORS(app)

# Configuration de la clé secrète pour signer les tokens JWT
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "super-cle-secrete-a-changer-en-production")
jwt = JWTManager(app)

# Enregistrement des routes modulaires (Blueprints)
app.register_blueprint(users_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(alerts_bp)   # ← routes /api/alerts ajoutées

if __name__ == "__main__":
    app.run(debug=True)