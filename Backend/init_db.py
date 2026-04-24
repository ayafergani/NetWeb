from Database.db import get_db_connection
from Database.interface import initialize_default_interfaces
from utils.security import hash_password


def init_database():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        print("Creation de la table 'utilisateur'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS utilisateur (
                id_user SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL
            );
        """)

        print("Insertion de l'administrateur par defaut...")
        hashed_pw = hash_password("123").decode("utf-8")
        cursor.execute(
            """
            INSERT INTO utilisateur (username, email, password, role)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (username) DO NOTHING;
            """,
            ("admin", "admin@netguard.local", hashed_pw, "ADMIN")
        )

        conn.commit()
        cursor.close()
        conn.close()

        inserted_count = initialize_default_interfaces()
        print(
            "Base de donnees initialisee avec succes. "
            f"{inserted_count} interfaces Cisco 9200 ajoutees si absentes."
        )
    except Exception as e:
        print(f"Erreur lors de l'initialisation : {e}")


if __name__ == "__main__":
    init_database()
