from Database.db import get_db_connection
from utils.security import hash_password
import psycopg2

def init_database():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Création de la table 'utilisateur'
        print("Création de la table 'utilisateur'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS utilisateur (
    init              id_user SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL
            );
        """)
        
        # 2. Hachage du mot de passe '123' et insertion
        print("Insertion de l'administrateur...")
        hashed_pw = hash_password("123").decode('utf-8')
        cursor.execute(
            "INSERT INTO utilisateur (username, email, password, role) VALUES (%s, %s, %s, %s) ON CONFLICT (username) DO NOTHING;",
            ("admin", "admin@netguard.local", hashed_pw, "ADMIN")
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Base de données initialisée avec succès ! L'utilisateur 'admin' avec le mot de passe '123' a été créé.")
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation : {e}")

if __name__ == "__main__":
    init_database()
