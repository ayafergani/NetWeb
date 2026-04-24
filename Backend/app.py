from flask import Flask
from flask_jwt_extended import JWTManager
from users import users_bp
from auth import auth_bp
from Database.alerts import alerts_bp
from Database.traffic import traffic_bp
from Database.regles import regles_bp
from Database.vlan import vlan_bp
# from vlan_api import vlan_bp # <-- Importer le nouveau fichier
from network_api import network_bp
import os
from flask_cors import CORS

app = Flask(__name__)

# Autoriser les requetes CORS provenant du frontend
CORS(app)

# Configuration de la cle secrete pour signer les tokens JWT
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "super-cle-secrete-a-changer-en-production")
jwt = JWTManager(app)

# Enregistrement des routes modulaires (Blueprints)
app.register_blueprint(users_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(alerts_bp)
app.register_blueprint(traffic_bp)
app.register_blueprint(regles_bp)
app.register_blueprint(vlan_bp)

# app.register_blueprint(vlan_bp)      # <-- Enregistrer la nouvelle route
app.register_blueprint(network_bp)   # ← routes /api/network

if __name__ == "__main__":
    app.run(debug=True, host='127.0.0.1', port=5000)
    app.run(debug=True)
