from flask import Flask
from flask_jwt_extended import JWTManager
from users import users_bp
from auth import auth_bp
from Database.alerts import alerts_bp
from Database.traffic import traffic_bp
from Database.regles import regles_bp
from Database.vlan import vlan_bp
from Database.interface import interface_bp, initialize_default_interfaces
# from vlan_api import vlan_bp # <-- Importer le nouveau fichier
from network_api import network_bp
from equipements_api import equipements_bp

import os
import logging
from flask_cors import CORS

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

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
app.register_blueprint(interface_bp)
try:
    initialize_default_interfaces()
except Exception as e:
    app.logger.error("Initialisation des interfaces impossible: %s", e)

# app.register_blueprint(vlan_bp)      # <-- Enregistrer la nouvelle route
app.register_blueprint(network_bp)   # ← routes /api/network
# app.register_blueprint(equipements_bp)  # ← routes /api/equipements
app.register_blueprint(equipements_bp)
if __name__ == "__main__":
    app.run(debug=True, host='127.0.0.1', port=5000)
