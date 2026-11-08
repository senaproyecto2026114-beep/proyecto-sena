from database import db
from datetime import datetime, date, time
from typing import Optional
import re
import pytz
import mysql.connector

class CRUD:
    @staticmethod
    def verificar_admin(username: str, password: str):
        connection = db.connect()
        if connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM administradores WHERE LOWER(TRIM(username)) = LOWER(TRIM(%s)) AND password = %s",
                (username, password)
            )
            admin = cursor.fetchone()
            cursor.close()
            db.disconnect(connection)
            return admin
        return None

    @staticmethod
    def existe_admin_por_username(username: str) -> bool:
        connection = db.connect()
        if connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT id FROM administradores WHERE LOWER(TRIM(username)) = LOWER(TRIM(%s))",
                (username,),
            )
            existe = cursor.fetchone() is not None
            cursor.close()
            db.disconnect(connection)
            return existe
        return False

    @staticmethod
    def actualizar_password_admin(username: str, nueva_password: str) -> bool:
        connection = db.connect()
        if connection:
            cursor = connection.cursor()
            try:
                cursor.execute(
                    "UPDATE administradores SET password = %s WHERE LOWER(TRIM(username)) = LOWER(TRIM(%s))",
                    (nueva_password, username),
                )
                connection.commit()
                ok = cursor.rowcount > 0
            finally:
                cursor.close()
                db.disconnect(connection)
            return ok
        return False

    @staticmethod
    def obtener_admin_por_username(username: str):
        connection = db.connect()
        if connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM administradores WHERE LOWER(TRIM(username)) = LOWER(TRIM(%s))",
                (username,),
            )
            admin = cursor.fetchone()
            cursor.close()
            db.disconnect(connection)
            return admin
        return None

    @staticmethod
    def contar_administradores() -> int:
        connection = db.connect()
        if connection:
            cursor = connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM administradores")
            (total,) = cursor.fetchone()
            cursor.close()
            db.disconnect(connection)
            return int(total or 0)
        return 0

    @staticmethod
    def contar_administradores_por_rol(rol: str) -> int:
        connection = db.connect()
        if connection:
            cursor = connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM administradores WHERE rol = %s", (rol,))
            (total,) = cursor.fetchone()
            cursor.close()
            db.disconnect(connection)
            return int(total or 0)
        return 0

    @staticmethod
    def crear_admin(
        username: str,
        password: str,
        nombre_completo: str,
        email: str,
        celular: str,
        numero_documento: str,
        rol: str,
        grados: str = "",
        primer_nombre: str = "",
        segundo_nombre: str = "",
        primer_apellido: str = "",
        segundo_apellido: str = "",
    ):
        """
        Crea un nuevo administrador.
        Tabla administradores: username, password, nombre (completo),
        primer_nombre, segundo_nombre, primer_apellido, segundo_apellido,
        email, celular, documento, rol, grados.
        Ver backend/sql/administradores.sql para columnas faltantes.
        """
        connection = db.connect()
        if connection:
            cursor = connection.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO administradores
                    (username, password, nombre,
                     primer_nombre, segundo_nombre, primer_apellido, segundo_apellido,
                     email, celular, documento, rol, grados)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        username,
                        password,
                        nombre_completo,
                        primer_nombre or None,
                        segundo_nombre or None,
                        primer_apellido or None,
                        segundo_apellido or None,
                        email,
                        celular,
                        numero_documento,
                        rol,
                        grados or None,
                    ),
                )
                connection.commit()
                admin_id = cursor.lastrowid
            except mysql.connector.Error:
                connection.rollback()
                raise
            finally:
                cursor.close()
                db.disconnect(connection)
            return admin_id
        return None
    
    @staticmethod
    def obtener_estudiantes():
        connection = db.connect()
        if connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM estudiantes WHERE activo = TRUE")
            estudiantes = cursor.fetchall()
            cursor.close()
            db.disconnect(connection)
            return estudiantes
        return []
    
    @staticmethod
    def _normalizar_grado(grado: str) -> str:
        s = (grado or "").strip()
        return re.sub(r"\s+", "", s)

    @staticmethod
    def registrar_asistencia(
        estudiante_id: int,
        hora_ingreso: time,
        dia_semana: Optional[str] = None,
    ):
        """Inserta asistencia. Devuelve 'PUNTUAL', 'TARDE' o None si falla."""
        connection = db.connect()
        if connection:
            cursor = connection.cursor()

            # Determinar tipo de ingreso
            hora_limite = time(7, 0, 0)  # 7:00 AM
            tipo_ingreso = "TARDE" if hora_ingreso > hora_limite else "PUNTUAL"

            # Obtener día de la semana en español
            dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            if dia_semana is None:
                dia_semana = dias_semana[datetime.now().weekday()]

            # Insertar registro
            cursor.execute("""
                INSERT INTO registros_asistencia 
                (estudiante_id, fecha, hora, tipo_ingreso, dia_semana)
                VALUES (%s, CURDATE(), %s, %s, %s)
            """, (estudiante_id, hora_ingreso, tipo_ingreso, dia_semana))

            connection.commit()
            cursor.close()
            db.disconnect(connection)
            return tipo_ingreso
        return None

    @staticmethod
    def contar_tardanzas_estudiante(estudiante_id: int) -> int:
        """Total de registros con tipo TARDE para el estudiante (incluye el actual)."""
        connection = db.connect()
        if connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) FROM registros_asistencia
                WHERE estudiante_id = %s AND tipo_ingreso = 'TARDE'
                """,
                (estudiante_id,),
            )
            (n,) = cursor.fetchone()
            cursor.close()
            db.disconnect(connection)
            return int(n or 0)
        return 0

    @staticmethod
    def obtener_coordinador_por_grado(grado: str):
        """
        Primer coordinador cuyo campo grados (CSV) incluye el grado del estudiante.
        """
        g = CRUD._normalizar_grado(grado)
        if not g:
            return None
        connection = db.connect()
        if connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT id, nombre, celular, grados
                FROM administradores
                WHERE rol = 'COORDINADOR'
                  AND grados IS NOT NULL
                  AND TRIM(grados) != ''
                """
            )
            rows = cursor.fetchall()
            cursor.close()
            db.disconnect(connection)
            for row in rows:
                partes = (row.get("grados") or "").split(",")
                normalizados = {CRUD._normalizar_grado(p) for p in partes if p.strip()}
                if g in normalizados:
                    return row
        return None
    
    @staticmethod
    def obtener_registros_por_fecha(fecha_inicio: date, fecha_fin: date):
        connection = db.connect()
        if connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT ra.*, e.nombre_completo, e.grado 
                FROM registros_asistencia ra
                JOIN estudiantes e ON ra.estudiante_id = e.id
                WHERE ra.fecha BETWEEN %s AND %s
                ORDER BY ra.fecha DESC, ra.hora DESC
            """, (fecha_inicio, fecha_fin))
            registros = cursor.fetchall()
            cursor.close()
            db.disconnect(connection)
            return registros
        return []
    
    @staticmethod
    def obtener_historial_estudiante(estudiante_id: int):
        connection = db.connect()
        if connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT * FROM registros_asistencia 
                WHERE estudiante_id = %s 
                ORDER BY fecha DESC, hora DESC
            """, (estudiante_id,))
            historial = cursor.fetchall()
            cursor.close()
            db.disconnect(connection)
            return historial
        return []
    
    @staticmethod
    def buscar_estudiante_por_huella(huella: str):
        connection = db.connect()
        if connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM estudiantes WHERE huella_dactilar = %s AND activo = TRUE",
                (huella,)
            )
            estudiante = cursor.fetchone()
            cursor.close()
            db.disconnect(connection)
            return estudiante
        return None

    @staticmethod
    def obtener_estudiante_por_id(estudiante_id: int):
        connection = db.connect()
        if connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM estudiantes WHERE id = %s AND activo = TRUE",
                (estudiante_id,),
            )
            estudiante = cursor.fetchone()
            cursor.close()
            db.disconnect(connection)
            return estudiante
        return None
    
    @staticmethod
    def agregar_estudiante(nombre: str, grado: str, codigo: str, huella: str = None):
        connection = db.connect()
        if connection:
            cursor = connection.cursor()
            cursor.execute("""
                INSERT INTO estudiantes (nombre_completo, grado, codigo_estudiante, huella_dactilar)
                VALUES (%s, %s, %s, %s)
            """, (nombre, grado, codigo, huella))
            connection.commit()
            estudiante_id = cursor.lastrowid
            cursor.close()
            db.disconnect(connection)
            return estudiante_id
        return None
    
    @staticmethod
    def obtener_estadisticas():
        connection = db.connect()
        if connection:
            cursor = connection.cursor(dictionary=True)
            
            # Total estudiantes
            cursor.execute("SELECT COUNT(*) as total FROM estudiantes WHERE activo = TRUE")
            total_estudiantes = cursor.fetchone()
            
            # Asistencias hoy
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN tipo_ingreso = 'PUNTUAL' THEN 1 END) as puntuales,
                    COUNT(CASE WHEN tipo_ingreso = 'TARDE' THEN 1 END) as tardes
                FROM registros_asistencia 
                WHERE fecha = CURDATE()
            """)
            hoy = cursor.fetchone()
            
            # Tardes esta semana
            cursor.execute("""
                SELECT COUNT(*) as tardes_semana 
                FROM registros_asistencia 
                WHERE tipo_ingreso = 'TARDE' 
                AND fecha >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            """)
            semana = cursor.fetchone()
            
            cursor.close()
            db.disconnect(connection)
            
            return {
                'total_estudiantes': total_estudiantes['total'],
                'hoy': hoy,
                'semana': semana['tardes_semana']
            }
        return None