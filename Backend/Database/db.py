import psycopg2
from psycopg2 import pool
import os

# Connection pool
db_pool = None

def init_db_pool():
    global db_pool
    db_pool = psycopg2.pool.SimpleConnectionPool(
        1, 20,
        dbname=os.getenv('DB_NAME', 'ids_db'),
        user=os.getenv('DB_USER', 'aya'),
        password=os.getenv('DB_PASSWORD', 'aya'),
        host=os.getenv('DB_HOST', '192.168.1.2'),
        port=os.getenv('DB_PORT', '5432')
    )
    return db_pool

def get_db_connection():
    if db_pool is None:
        init_db_pool()
    return db_pool.getconn()

def return_db_connection(conn):
    if db_pool:
        db_pool.putconn(conn)