from flask import request, jsonify
from utils.security import check_password

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data["username"]
    password = data["password"]

    # récupérer user depuis DB
    # vérifier password

    return jsonify({"message": "login success"})