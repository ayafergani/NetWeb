import bcrypt

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed)

password = b"123"
hashed = bcrypt.hashpw(password, bcrypt.gensalt())

print(hashed.decode())