import psycopg2

conn = psycopg2.connect(
    dbname="ids_db",
    user="aya",
    password="aya",
    host="192.168.1.2"
)