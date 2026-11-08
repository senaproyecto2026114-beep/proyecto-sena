from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from datetime import datetime, date as date_type, time as time_type
from typing import List
import pytz
import os
import re
import mysql.connector
from mysql.connector import Error as MySQLError
import time
import random
import string
import smtplib
from email.mime.text import MIMEText
from pathlib import Path
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import tempfile

from database import db
from schemas import *
from crud import CRUD
from whatsapp_envio import enviar_mensaje_whatsapp, normalizar_telefono_whatsapp

load_dotenv(Path(__file__).resolve().parent / ".env")

_BOGOTA_TZ = pytz.timezone("America/Bogota")

app = FastAPI(title="API Control de Asistencia con Huella Digital")


def _plantilla_whatsapp_tardanza(
    nombre_estudiante: str, fecha_dd_mm_yyyy: str, hora_hh_mm_ss: str, numero_tarde: int
) -> str:
    return (
        f'Buen día coordinador(a). El estudiante "{nombre_estudiante}" ha llegado tarde el día de hoy '
        f"{fecha_dd_mm_yyyy} a las {hora_hh_mm_ss}. Es la llegada tarde No. {numero_tarde}."
    )


def notificar_coordinador_tardanza(
    estudiante_id: int,
    nombre_completo: str,
    grado: str,
    hora_ingreso: time_type,
) -> dict:
    """
    Arma el mensaje oficial, elige el celular del coordinador del grado (tabla administradores)
    o WHATSAPP_FALLBACK_NUMERO en .env. Envío real con Twilio si TWILIO_* está configurado.
    """
    ahora = datetime.now(_BOGOTA_TZ)
    fecha_str = ahora.strftime("%d-%m-%Y")
    hora_str = hora_ingreso.strftime("%H:%M:%S")
    n = CRUD.contar_tardanzas_estudiante(estudiante_id)
    coord = CRUD.obtener_coordinador_por_grado(grado)
    cel = (coord or {}).get("celular")
    fallback = (os.getenv("WHATSAPP_FALLBACK_NUMERO") or "573178668782").strip()
    raw = (cel or fallback or "").strip()
    telefono = normalizar_telefono_whatsapp(raw)
    mensaje = _plantilla_whatsapp_tardanza(nombre_completo, fecha_str, hora_str, n)
    if not telefono:
        print(f"[WhatsApp] Sin número válido. Mensaje: {mensaje}")
        return {
            "enviado": False,
            "motivo": "sin_telefono",
            "mensaje": mensaje,
            "coordinador_encontrado": coord is not None,
        }
    send = enviar_mensaje_whatsapp(telefono, mensaje)
    if not send["ok"]:
        return {
            "enviado": False,
            "motivo": "twilio_error",
            "error": send.get("detalle"),
            "mensaje": mensaje,
            "coordinador_encontrado": coord is not None,
            "modo": send.get("modo"),
        }
    return {
        "enviado": True,
        "telefono_destino": telefono,
        "mensaje": mensaje,
        "coordinador_encontrado": coord is not None,
        "modo": send["modo"],
        "twilio_sid": send["detalle"] if send["modo"] == "twilio" else None,
    }

# CORS: con fetch sin cookies, allow_credentials=False + "*" evita "Failed to fetch" desde cualquier puerto/host local.
# Para producción, defina CORS_ORIGINS en .env (lista separada por comas) y use orígenes explícitos.
_cors_extra = os.getenv("CORS_ORIGINS", "").strip()
if _cors_extra:
    _cors_list = [o.strip() for o in _cors_extra.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Ruta principal
@app.get("/")
def read_root():
    return {"message": "API de Control de Asistencia con Huella Digital"}

# Códigos de recuperación de contraseña (usuario -> (código, tiempo_expiración))
_reset_codes = {}
_RESET_CODE_EXPIRY_SECONDS = 15 * 60  # 15 minutos

def _limpiar_codigos_expirados():
    now = time.time()
    global _reset_codes
    _reset_codes = {u: v for u, v in _reset_codes.items() if v[1] > now}

def _generar_codigo():
    return "".join(random.choices(string.digits, k=6))


def _enviar_correo_reset(destinatario: str, codigo: str):
    """
    Envía un correo con el código de verificación para restablecer contraseña.
    Requiere configuración en variables de entorno:
    MAIL_HOST, MAIL_PORT, MAIL_USER, MAIL_PASSWORD, MAIL_FROM
    """
    host = (os.getenv("MAIL_HOST") or "").strip()
    port = int((os.getenv("MAIL_PORT") or "587").strip())
    user = (os.getenv("MAIL_USER") or "").strip()
    password = (os.getenv("MAIL_PASSWORD") or "").strip()
    # Gmail: la contraseña de aplicaciones son 16 caracteres; quitar espacios evita fallos al copiar/pegar
    if "smtp.gmail.com" in host.lower():
        password = re.sub(r"\s+", "", password)
    remitente = (os.getenv("MAIL_FROM") or user or "").strip()

    faltan = []
    if not host:
        faltan.append("MAIL_HOST")
    if not user:
        faltan.append("MAIL_USER")
    if not password:
        faltan.append("MAIL_PASSWORD")
    if not remitente:
        faltan.append("MAIL_FROM")
    if faltan:
        raise HTTPException(
            status_code=500,
            detail=(
                "Falta configurar el correo en el archivo backend/.env (copie desde .env.example). "
                "Variables vacías o ausentes: " + ", ".join(faltan) + ". "
                "Reinicie uvicorn después de guardar .env."
            ),
        )

    mensaje = MIMEText(
        f"Se ha solicitado restablecer la contraseña de su cuenta.\n\n"
        f"Su código de verificación es: {codigo}\n\n"
        f"Este código es válido por 15 minutos.\n\n"
        f"Si usted no solicitó este cambio, ignore este mensaje.",
        "plain",
        "utf-8",
    )
    mensaje["Subject"] = "Código para restablecer contraseña - Sistema de Asistencia"
    mensaje["From"] = remitente
    mensaje["To"] = destinatario

    try:
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(mensaje)
    except Exception as e:
        msg = str(e)
        extra = ""
        if "535" in msg or "BadCredentials" in msg or "Username and Password not accepted" in msg:
            extra = (
                " Gmail: MAIL_USER debe ser el correo completo (ej. usuario@gmail.com). "
                "MAIL_PASSWORD debe ser una contraseña de APLICACIONES (Cuenta Google → Seguridad → "
                "Verificación en 2 pasos → Contraseñas de aplicaciones), no la clave con la que entra al navegador. "
                "Si la acaba de crear, espere 1–2 minutos y reinicie uvicorn."
            )
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo enviar el correo de recuperación: {msg}.{extra}",
        )

# Login de administrador
@app.post("/api/login")
def login(admin: AdminLogin):
    usuario = CRUD.verificar_admin(admin.username, admin.password)
    if usuario:
        return {
            "success": True,
            "admin": {
                "id": usuario["id"],
                "nombre": usuario["nombre"],
                "username": usuario["username"]
            }
        }
    raise HTTPException(status_code=401, detail="Credenciales incorrectas")

# Solicitar código para recuperar contraseña
@app.post("/api/olvide-clave/solicitar")
def solicitar_codigo_recuperacion(data: SolicitarCodigoRecuperacion):
    _limpiar_codigos_expirados()
    username = (data.username or "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="Ingrese su usuario")
    # Misma clave que al registrar (correo en minúsculas) y para restablecer
    username_key = username.lower()
    admin = CRUD.obtener_admin_por_username(username)
    if not admin:
        raise HTTPException(status_code=404, detail="No existe un administrador con ese usuario")
    # Correo para envío: columna email o, si viene vacía, el username (correo de login)
    email = (admin.get("email") or admin.get("username") or "").strip()
    if not email:
        raise HTTPException(
            status_code=400,
            detail="El administrador no tiene un correo registrado. Contacte al administrador del sistema.",
        )
    codigo = _generar_codigo()
    _reset_codes[username_key] = (codigo, time.time() + _RESET_CODE_EXPIRY_SECONDS)
    # Enviar código por correo
    _enviar_correo_reset(email, codigo)
    return {
        "success": True,
        "mensaje": "Se ha enviado un código de verificación al correo registrado. Revíselo y úselo en los próximos 15 minutos.",
    }

# Restablecer contraseña con el código
@app.post("/api/olvide-clave/restablecer")
def restablecer_clave(data: RestablecerClave):
    _limpiar_codigos_expirados()
    username = (data.username or "").strip()
    username_key = username.lower()
    codigo = (data.codigo or "").strip()
    nueva_clave = (data.nueva_clave or "").strip()
    if not username or not codigo or not nueva_clave:
        raise HTTPException(status_code=400, detail="Complete usuario, código y nueva contraseña")
    # Validación fuerte de contraseña: mínimo 8 caracteres, mayúscula, minúscula, número y símbolo
    if len(nueva_clave) < 8:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 8 caracteres")
    if not any(c.islower() for c in nueva_clave) or not any(c.isupper() for c in nueva_clave):
        raise HTTPException(status_code=400, detail="La contraseña debe incluir letras mayúsculas y minúsculas")
    if not any(c.isdigit() for c in nueva_clave):
        raise HTTPException(status_code=400, detail="La contraseña debe incluir al menos un número")
    if not any(not c.isalnum() for c in nueva_clave):
        raise HTTPException(status_code=400, detail="La contraseña debe incluir al menos un símbolo")
    if username_key not in _reset_codes:
        raise HTTPException(status_code=400, detail="Código no solicitado o expirado. Solicite uno nuevo.")
    codigo_guardado, expiry = _reset_codes[username_key]
    if time.time() > expiry:
        del _reset_codes[username_key]
        raise HTTPException(status_code=400, detail="El código ha expirado. Solicite uno nuevo.")
    if codigo != codigo_guardado:
        raise HTTPException(status_code=400, detail="Código incorrecto")
    if not CRUD.actualizar_password_admin(username_key, nueva_clave):
        raise HTTPException(status_code=500, detail="No se pudo actualizar la contraseña")
    del _reset_codes[username_key]
    return {"success": True, "mensaje": "Contraseña actualizada. Ya puede iniciar sesión con su nueva contraseña."}


# Registro de administradores (hasta 3: 2 coordinadores y 1 rectora)
@app.post("/api/admins/registrar")
def registrar_admin(admin: AdminRegistro):
    # Máximo 3 administradores en total
    total_admins = CRUD.contar_administradores()
    if total_admins >= 3:
        raise HTTPException(
            status_code=400,
            detail="Ya existen 3 administradores registrados (2 coordinadores y 1 rectora).",
        )

    # Validar rol y límites por rol
    rol = admin.rol.upper()
    if rol not in ("COORDINADOR", "RECTORA"):
        raise HTTPException(status_code=400, detail="Rol no válido")

    if rol == "COORDINADOR":
        coordinadores = CRUD.contar_administradores_por_rol("COORDINADOR")
        if coordinadores >= 2:
            raise HTTPException(
                status_code=400,
                detail="Ya existen 2 coordinadores registrados.",
            )
        if not admin.grados or len(admin.grados) == 0:
            raise HTTPException(
                status_code=400,
                detail="Debe seleccionar al menos un grado a cargo para el coordinador.",
            )
    else:  # RECTORA
        rectoras = CRUD.contar_administradores_por_rol("RECTORA")
        if rectoras >= 1:
            raise HTTPException(
                status_code=400,
                detail="Ya existe una rectora registrada.",
            )

    # Validar que el correo (que será usado como usuario) no exista
    username = admin.correo.strip().lower()
    if CRUD.existe_admin_por_username(username):
        raise HTTPException(status_code=400, detail="Ya existe un administrador con ese correo (usuario).")

    # Validar contraseña fuerte
    password = admin.password or ""
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 8 caracteres")
    if not any(c.islower() for c in password) or not any(c.isupper() for c in password):
        raise HTTPException(status_code=400, detail="La contraseña debe incluir letras mayúsculas y minúsculas")
    if not any(c.isdigit() for c in password):
        raise HTTPException(status_code=400, detail="La contraseña debe incluir al menos un número")
    if not any(not c.isalnum() for c in password):
        raise HTTPException(status_code=400, detail="La contraseña debe incluir al menos un símbolo")

    # Construir nombre completo
    nombre_partes = [
        admin.primer_nombre.strip(),
        (admin.segundo_nombre or "").strip(),
        admin.primer_apellido.strip(),
        (admin.segundo_apellido or "").strip(),
    ]
    nombre_completo = " ".join([p for p in nombre_partes if p])

    grados_txt = ""
    if admin.grados:
        grados_txt = ",".join(admin.grados)

    try:
        admin_id = CRUD.crear_admin(
            username=username,
            password=password,
            nombre_completo=nombre_completo,
            email=admin.correo,
            celular=admin.celular,
            numero_documento=admin.numero_documento,
            rol=rol,
            grados=grados_txt,
            primer_nombre=admin.primer_nombre.strip(),
            segundo_nombre=(admin.segundo_nombre or "").strip(),
            primer_apellido=admin.primer_apellido.strip(),
            segundo_apellido=(admin.segundo_apellido or "").strip(),
        )
    except MySQLError as e:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Error al guardar en la base de datos: {str(e)}. "
                "Revise que la tabla administradores tenga las columnas de backend/sql/administradores.sql."
            ),
        )
    if not admin_id:
        raise HTTPException(status_code=500, detail="No se pudo registrar el administrador.")

    return {
        "success": True,
        "id": admin_id,
        "mensaje": "Administrador registrado correctamente. Ya puede iniciar sesión con su correo y contraseña.",
    }

# Registrar huella desde Arduino
@app.post("/api/registrar-huella")
def registrar_huella(huella_data: dict):
    huella = huella_data.get("huella")
    if not huella:
        raise HTTPException(status_code=400, detail="Huella no proporcionada")
    
    estudiante = CRUD.buscar_estudiante_por_huella(huella)
    if not estudiante:
        return {"encontrado": False, "mensaje": "Huella no registrada"}
    
    # Registrar asistencia (hora y día según Bogotá)
    ahora = datetime.now(_BOGOTA_TZ)
    hora_actual = ahora.time()
    dias_semana = [
        "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"
    ]
    dia_semana = dias_semana[ahora.weekday()]
    tipo_ingreso = CRUD.registrar_asistencia(
        estudiante["id"], hora_actual, dia_semana
    )
    whatsapp_coordinador = None
    if tipo_ingreso == "TARDE":
        whatsapp_coordinador = notificar_coordinador_tardanza(
            estudiante["id"],
            estudiante["nombre_completo"],
            estudiante["grado"],
            hora_actual,
        )

    return {
        "encontrado": True,
        "estudiante": {
            "id": estudiante["id"],
            "nombre": estudiante["nombre_completo"],
            "grado": estudiante["grado"],
        },
        "hora": hora_actual.strftime("%H:%M:%S"),
        "tipo_ingreso": tipo_ingreso,
        "mensaje": "BIENVENIDO " + estudiante["nombre_completo"],
        "whatsapp_coordinador": whatsapp_coordinador,
    }


@app.post("/api/asistencia/sensor")
def asistencia_desde_sensor_slot(data: AsistenciaDesdeSensor):
    """
    Registra asistencia cuando el Arduino reconoce una huella en el AS608.
    El ID devuelto por el sensor (slot 1-127) debe ser el mismo que estudiantes.id.
    La cadena huella_dactilar en la BD (ej. huella_fdt519cl0) no se usa aquí:
    el sensor solo compara contra plantillas grabadas en su memoria flash.
    """
    estudiante = CRUD.obtener_estudiante_por_id(data.estudiante_id)
    if not estudiante:
        raise HTTPException(
            status_code=404,
            detail="No hay estudiante activo con ese id. Enrolle en el sensor el mismo número que el id en la base de datos.",
        )

    ahora = datetime.now(_BOGOTA_TZ)
    hora_actual = ahora.time()
    dias_semana = [
        "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"
    ]
    dia_semana = dias_semana[ahora.weekday()]
    tipo_ingreso = CRUD.registrar_asistencia(
        estudiante["id"], hora_actual, dia_semana
    )
    if tipo_ingreso is None:
        raise HTTPException(status_code=500, detail="No se pudo registrar la asistencia")

    whatsapp_coordinador = None
    if tipo_ingreso == "TARDE":
        whatsapp_coordinador = notificar_coordinador_tardanza(
            estudiante["id"],
            estudiante["nombre_completo"],
            estudiante["grado"],
            hora_actual,
        )

    return {
        "ok": True,
        "estudiante": {
            "id": estudiante["id"],
            "nombre": estudiante["nombre_completo"],
            "grado": estudiante["grado"],
        },
        "hora": hora_actual.strftime("%H:%M:%S"),
        "tipo_ingreso": tipo_ingreso,
        "confianza": data.confianza,
        "mensaje": "BIENVENIDO " + estudiante["nombre_completo"],
        "whatsapp_coordinador": whatsapp_coordinador,
    }

# Obtener todos los estudiantes
@app.get("/api/estudiantes", response_model=List[dict])
def obtener_estudiantes():
    estudiantes = CRUD.obtener_estudiantes()
    return estudiantes

# Obtener registros por fecha
@app.post("/api/registros/fecha")
def obtener_registros_por_fecha(filtro: FiltroFecha):
    registros = CRUD.obtener_registros_por_fecha(filtro.fecha_inicio, filtro.fecha_fin)
    return registros


@app.delete("/api/registros")
def eliminar_todo_historial():
    """
    Borra todo el historial de asistencia.
    Uso recomendado solo en pruebas.
    """
    connection = db.connect()
    if not connection:
        raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")
    cursor = connection.cursor()
    try:
        cursor.execute("DELETE FROM registros_asistencia")
        eliminados = cursor.rowcount
        connection.commit()
        return {"message": "Historial eliminado", "registros_eliminados": int(eliminados or 0)}
    except mysql.connector.Error as e:
        connection.rollback()
        raise HTTPException(status_code=500, detail=f"No se pudo eliminar el historial: {str(e)}")
    finally:
        cursor.close()
        db.disconnect(connection)

# Obtener historial de estudiante
@app.get("/api/estudiante/{estudiante_id}/historial")
def obtener_historial_estudiante(estudiante_id: int):
    historial = CRUD.obtener_historial_estudiante(estudiante_id)
    return historial

# Generar PDF de historial
@app.get("/api/estudiante/{estudiante_id}/pdf")
def generar_pdf_historial(estudiante_id: int):
    # Obtener información del estudiante
    connection = db.connect()
    if not connection:
        raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM estudiantes WHERE id = %s", (estudiante_id,))
    estudiante = cursor.fetchone()
    cursor.close()
    db.disconnect(connection)
    if not estudiante:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")

    # Obtener historial
    historial = CRUD.obtener_historial_estudiante(estudiante_id)
    
    # Crear PDF temporal
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf_path = temp_file.name
    
    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter
    
    # Encabezado
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Institución Educativa Nuestra Señora de Chiquinquirá")
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 70, "Historial de Asistencia")
    
    # Información del estudiante
    c.drawString(50, height - 100, f"Estudiante: {estudiante['nombre_completo']}")
    c.drawString(50, height - 115, f"Grado: {estudiante['grado']}")
    c.drawString(50, height - 130, f"Código: {estudiante['codigo_estudiante']}")
    
    # Tabla de registros
    y = height - 170
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Fecha")
    c.drawString(150, y, "Hora")
    c.drawString(230, y, "Día")
    c.drawString(300, y, "Tipo")
    
    c.setFont("Helvetica", 10)
    y -= 20
    
    for registro in historial:
        if y < 100:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 10)
        
        c.drawString(50, y, str(registro['fecha']))
        c.drawString(150, y, str(registro['hora']))
        c.drawString(230, y, registro['dia_semana'])
        c.drawString(300, y, registro['tipo_ingreso'])
        y -= 15
    
    # Pie de página
    c.setFont("Helvetica", 8)
    c.drawString(50, 50, "Generado automáticamente por el Sistema de Control de Asistencia")
    c.drawString(50, 40, "NI UNA LLEGADA TARDE MÁS")
    
    c.save()
    temp_file.close()
    
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"historial_{estudiante['nombre_completo'].replace(' ', '_')}.pdf"
    )


@app.get("/api/estudiante/{estudiante_id}/pdf-tardanzas")
def generar_pdf_tardanzas_estudiante(
    estudiante_id: int,
    fecha_inicio: str | None = None,
    fecha_fin: str | None = None,
):
    connection = db.connect()
    if not connection:
        raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")

    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, nombre_completo, grado, codigo_estudiante FROM estudiantes WHERE id = %s",
        (estudiante_id,),
    )
    estudiante = cursor.fetchone()
    if not estudiante:
        cursor.close()
        db.disconnect(connection)
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")

    fi: date_type | None = None
    ff: date_type | None = None
    try:
        fi = datetime.strptime(fecha_inicio, "%Y-%m-%d").date() if fecha_inicio else None
        ff = datetime.strptime(fecha_fin, "%Y-%m-%d").date() if fecha_fin else None
    except ValueError:
        cursor.close()
        db.disconnect(connection)
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD.")

    query = """
        SELECT fecha, hora, dia_semana, tipo_ingreso
        FROM registros_asistencia
        WHERE estudiante_id = %s
          AND tipo_ingreso = 'TARDE'
    """
    params: list = [estudiante_id]
    if fi:
        query += " AND fecha >= %s"
        params.append(fi)
    if ff:
        query += " AND fecha <= %s"
        params.append(ff)
    query += " ORDER BY fecha DESC, hora DESC"

    cursor.execute(query, tuple(params))
    tardanzas = cursor.fetchall()
    cursor.close()
    db.disconnect(connection)

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf_path = temp_file.name

    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter
    c.setFont("Helvetica-Bold", 15)
    c.drawString(50, height - 50, "Reporte de Llegadas Tarde")
    c.setFont("Helvetica", 11)
    c.drawString(50, height - 70, "Institución Educativa Nuestra Señora de Chiquinquirá")
    c.drawString(50, height - 95, f"Estudiante: {estudiante['nombre_completo']}")
    c.drawString(50, height - 110, f"Grado: {estudiante['grado']}")
    c.drawString(50, height - 125, f"Código: {estudiante['codigo_estudiante']}")

    if fi or ff:
        tramo = f"{fi.isoformat() if fi else 'Inicio'} a {ff.isoformat() if ff else 'Hoy'}"
        c.drawString(50, height - 140, f"Rango filtrado: {tramo}")

    y = height - 175
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Fecha")
    c.drawString(140, y, "Hora")
    c.drawString(220, y, "Día")
    c.drawString(320, y, "Tipo")
    y -= 18
    c.setFont("Helvetica", 10)

    if not tardanzas:
        c.drawString(50, y, "No hay llegadas tarde para el filtro seleccionado.")
    else:
        for row in tardanzas:
            if y < 80:
                c.showPage()
                y = height - 60
                c.setFont("Helvetica-Bold", 10)
                c.drawString(50, y, "Fecha")
                c.drawString(140, y, "Hora")
                c.drawString(220, y, "Día")
                c.drawString(320, y, "Tipo")
                y -= 18
                c.setFont("Helvetica", 10)
            c.drawString(50, y, str(row["fecha"]))
            c.drawString(140, y, str(row["hora"]))
            c.drawString(220, y, str(row["dia_semana"]))
            c.drawString(320, y, str(row["tipo_ingreso"]))
            y -= 14

    c.setFont("Helvetica", 8)
    c.drawString(50, 40, f"Total de tardanzas: {len(tardanzas)}")
    c.save()
    temp_file.close()

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"reporte_tardanzas_{estudiante['nombre_completo'].replace(' ', '_')}.pdf",
    )

# Obtener estadísticas
@app.get("/api/estadisticas")
def obtener_estadisticas():
    estadisticas = CRUD.obtener_estadisticas()
    return estadisticas

@app.post("/api/whatsapp")
def enviar_whatsapp(mensaje: WhatsAppMessage):
    tel = normalizar_telefono_whatsapp(mensaje.telefono)
    if not tel:
        raise HTTPException(status_code=400, detail="Número de teléfono no válido")
    r = enviar_mensaje_whatsapp(tel, mensaje.mensaje)
    if not r["ok"]:
        raise HTTPException(status_code=502, detail=f"Error al enviar con Twilio: {r.get('detalle')}")
    return {
        "success": True,
        "modo": r["modo"],
        "twilio_sid": r["detalle"] if r["modo"] == "twilio" else None,
        "mensaje": "Enviado por Twilio" if r["modo"] == "twilio" else "Simulado (configure TWILIO_* para envío real)",
    }


@app.post("/api/whatsapp/notificar-tardanza")
def whatsapp_notificar_tardanza(data: NotificarTardanza):
    """Misma plantilla que al registrar huella tarde: coordinador por grado o WHATSAPP_FALLBACK_NUMERO."""
    connection = db.connect()
    if not connection:
        raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, nombre_completo, grado FROM estudiantes WHERE id = %s AND activo = TRUE",
        (data.estudiante_id,),
    )
    estudiante = cursor.fetchone()
    cursor.close()
    db.disconnect(connection)
    if not estudiante:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")

    hora = datetime.now(_BOGOTA_TZ).time()
    info = notificar_coordinador_tardanza(
        estudiante["id"],
        estudiante["nombre_completo"],
        estudiante["grado"],
        hora,
    )
    return {"success": bool(info.get("enviado")), **info}

# CRUD para Estudiantes
@app.post("/api/estudiantes")
def crear_estudiante(estudiante: EstudianteCreate):
    connection = db.connect()
    if connection:
        cursor = connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO estudiantes (nombre_completo, grado, codigo_estudiante, huella_dactilar, activo)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                estudiante.nombre_completo,
                estudiante.grado,
                estudiante.codigo_estudiante,
                estudiante.huella_dactilar,
                estudiante.activo,
            ))
            estudiante_id = cursor.lastrowid
            huella_guardada = estudiante.huella_dactilar
            if not huella_guardada:
                huella_guardada = f"as608_slot_{estudiante_id}"
                cursor.execute(
                    "UPDATE estudiantes SET huella_dactilar = %s WHERE id = %s",
                    (huella_guardada, estudiante_id),
                )
            connection.commit()
            return {
                "id": estudiante_id,
                "huella_dactilar": huella_guardada,
                "message": "Estudiante creado exitosamente"
            }
        except mysql.connector.Error as e:
            connection.rollback()
            if e.errno == 1062:  # Duplicate entry
                raise HTTPException(status_code=400, detail="El código de estudiante ya existe")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            cursor.close()
            db.disconnect(connection)
    raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")

@app.get("/api/estudiantes/{estudiante_id}")
def obtener_estudiante(estudiante_id: int):
    connection = db.connect()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM estudiantes WHERE id = %s", (estudiante_id,))
        estudiante = cursor.fetchone()
        cursor.close()
        db.disconnect(connection)
        if estudiante:
            return estudiante
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")

@app.put("/api/estudiantes/{estudiante_id}")
def actualizar_estudiante(estudiante_id: int, estudiante: EstudianteCreate):
    connection = db.connect()
    if connection:
        cursor = connection.cursor()
        try:
            cursor.execute("""
                UPDATE estudiantes 
                SET nombre_completo = %s, grado = %s, codigo_estudiante = %s, 
                    huella_dactilar = %s, activo = %s
                WHERE id = %s
            """, (
                estudiante.nombre_completo,
                estudiante.grado,
                estudiante.codigo_estudiante,
                estudiante.huella_dactilar,
                estudiante.activo,
                estudiante_id,
            ))
            connection.commit()
            return {"message": "Estudiante actualizado exitosamente"}
        except mysql.connector.Error as e:
            if e.errno == 1062:
                raise HTTPException(status_code=400, detail="El código de estudiante ya existe")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            cursor.close()
            db.disconnect(connection)
    raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")

@app.delete("/api/estudiantes/{estudiante_id}")
def eliminar_estudiante(estudiante_id: int):
    connection = db.connect()
    if connection:
        cursor = connection.cursor()
        try:
            cursor.execute("DELETE FROM registros_asistencia WHERE estudiante_id = %s", (estudiante_id,))
            cursor.execute("DELETE FROM estudiantes WHERE id = %s", (estudiante_id,))
            affected_rows = cursor.rowcount
            connection.commit()
            if affected_rows > 0:
                return {"message": "Estudiante eliminado exitosamente"}
            raise HTTPException(status_code=404, detail="Estudiante no encontrado")
        except HTTPException:
            connection.rollback()
            raise
        except mysql.connector.Error as e:
            connection.rollback()
            raise HTTPException(status_code=500, detail=f"No se pudo eliminar el estudiante: {str(e)}")
        finally:
            cursor.close()
            db.disconnect(connection)
    raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)