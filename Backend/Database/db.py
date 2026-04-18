import psycopg2
import os

# Il est fortement conseillé de passer par des variables d'environnement
DB_NAME = os.getenv("DB_NAME", "ids_db")
DB_USER = os.getenv("DB_USER", "aya")
DB_PASSWORD = os.getenv("DB_PASSWORD", "aya")
DB_HOST = os.getenv("DB_HOST", "192.168.1.2")

def get_db_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST
    )
