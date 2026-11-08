import mysql.connector
from mysql.connector import Error
import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar .env desde la carpeta backend (no depende del directorio desde el que ejecute uvicorn)
load_dotenv(Path(__file__).resolve().parent / ".env")

class Database:
    def __init__(self):
        self.host = os.getenv('DB_HOST', 'localhost')
        self.user = os.getenv('DB_USER', 'root')
        self.password = os.getenv('DB_PASSWORD', '12345')
        self.database = os.getenv('DB_NAME', 'asistencia_colegio')
    
    def connect(self):
        """Crea una nueva conexión por petición. Cada petición debe cerrar la suya con disconnect(conn)."""
        try:
            return mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            return None
    
    def disconnect(self, connection=None):
        """Cierra la conexión indicada. Si no se pasa, no hace nada (compatible con uso por petición)."""
        if connection:
            try:
                connection.close()
            except Exception:
                pass

db = Database()