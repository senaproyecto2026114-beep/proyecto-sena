from pydantic import BaseModel, EmailStr
from datetime import date, time as Time
from typing import Optional, List, Literal

class AdminCreate(BaseModel):
    username: str
    password: str
    nombre: str
    email: Optional[str] = None


class AdminRegistro(BaseModel):
    primer_nombre: str
    segundo_nombre: Optional[str] = None
    primer_apellido: str
    segundo_apellido: Optional[str] = None
    numero_documento: str
    correo: EmailStr
    celular: str
    rol: Literal["COORDINADOR", "RECTORA"]
    grados: Optional[List[str]] = None  # Solo obligatorio para coordinadores
    password: str

class AdminLogin(BaseModel):
    username: str
    password: str

class EstudianteCreate(BaseModel):
    nombre_completo: str
    grado: str
    codigo_estudiante: str
    huella_dactilar: Optional[str] = None
    activo: bool = True

class EstudianteResponse(BaseModel):
    id: int
    nombre_completo: str
    grado: str
    codigo_estudiante: str
    activo: bool

class RegistroAsistencia(BaseModel):
    estudiante_id: int
    fecha: date
    hora: Time
    tipo_ingreso: str
    dia_semana: str

class RegistroResponse(BaseModel):
    id: int
    estudiante_id: int
    fecha: date
    hora: Time
    tipo_ingreso: str
    dia_semana: str
    nombre_estudiante: str
    grado: str

class FiltroFecha(BaseModel):
    fecha_inicio: date
    fecha_fin: date

class WhatsAppMessage(BaseModel):
    telefono: str
    mensaje: str


class NotificarTardanza(BaseModel):
    """Notificación manual con la plantilla oficial (mismo criterio que huella tarde)."""
    estudiante_id: int


class AsistenciaDesdeSensor(BaseModel):
    """
    El AS608 devuelve un ID de plantilla (1-127) al buscar en su memoria interna.
    Ese número debe coincidir con estudiantes.id en MySQL (ver enroll_as608.ino).
    """
    estudiante_id: int
    confianza: Optional[int] = None


class SolicitarCodigoRecuperacion(BaseModel):
    username: str


class RestablecerClave(BaseModel):
    username: str
    codigo: str
    nueva_clave: str