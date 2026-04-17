class User:
    def __init__(self, id, username, email, password, role):
        self.id = id
        self.username = username
        self.email = email
        self.password = password
        self.role = role

    @app.route("/users", methods=["POST"])
    def create_user():
        # insert into DB
        return {"message": "user created"}
    
    @app.route("/users", methods=["GET"])
    def get_users():
        return {"users": []}
    
    @app.route("/users/<int:id>", methods=["DELETE"])
    def delete_user(id):
        return {"message": "deleted"}