from datetime import datetime
from database import db

def init_database():
    connection = db.connect()
    if connection:
        cursor = connection.cursor()
        
        # Tabla de administradores
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS administradores (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                nombre VARCHAR(100) NOT NULL,
                email VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabla de estudiantes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS estudiantes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre_completo VARCHAR(100) NOT NULL,
                grado VARCHAR(10) NOT NULL,
                huella_dactilar TEXT,
                codigo_estudiante VARCHAR(20) UNIQUE,
                activo BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabla de registros de asistencia
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS registros_asistencia (
                id INT AUTO_INCREMENT PRIMARY KEY,
                estudiante_id INT NOT NULL,
                fecha DATE NOT NULL,
                hora TIME NOT NULL,
                tipo_ingreso ENUM('PUNTUAL', 'TARDE') NOT NULL,
                dia_semana VARCHAR(15),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id) ON DELETE CASCADE,
                INDEX idx_fecha (fecha)
            )
        """)
        
        connection.commit()
        cursor.close()
        db.disconnect(connection)

# Inicializar la base de datos
init_database()