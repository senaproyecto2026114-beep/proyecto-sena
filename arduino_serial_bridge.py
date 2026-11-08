"""
Puente USB: Arduino (monitor serial) -> API FastAPI.

El sketch huella_as608.ino imprime una linea JSON por cada huella reconocida:
  {"estudiante_id":9,"confianza":123}

Esa linea se reenvia a POST /api/asistencia/sensor para registrar asistencia
y disparar WhatsApp al coordinador si la llegada es TARDE (misma logica que el backend).

Uso (Windows, con el backend en marcha en el puerto 8000):

  cd backend
  ..\\venv\\Scripts\\activate
  pip install -r requirements.txt
  python arduino_serial_bridge.py --port COM3

Sustituya COM3 por el puerto que muestra el Administrador de dispositivos.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def post_asistencia(api_url: str, estudiante_id: int, confianza: int | None) -> dict | None:
    payload = {"estudiante_id": int(estudiante_id)}
    if confianza is not None:
        payload["confianza"] = int(confianza)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        api_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        print(body)
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return None


def enviar_nombre_lcd(ser, nombre: str | None) -> None:
    if not nombre:
        return
    limpio = str(nombre).replace("\r", " ").replace("\n", " ").strip()
    if not limpio:
        return
    # El Arduino escucha esta orden para mostrar "BIENVENIDO <nombre>" en LCD.
    ser.write((f"LCD_NOMBRE:{limpio}\n").encode("utf-8", errors="ignore"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Arduino serial -> /api/asistencia/sensor")
    parser.add_argument("--port", default="COM11", help="Puerto serie del Arduino (ej. COM11)")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument(
        "--api",
        default="http://127.0.0.1:8000/api/asistencia/sensor",
        help="URL completa del endpoint",
    )
    args = parser.parse_args()

    try:
        import serial
    except ImportError:
        print("Instale pyserial: pip install -r requirements.txt", file=sys.stderr)
        return 1

    try:
        ser = serial.Serial(args.port, args.baud, timeout=1)
    except serial.SerialException as e:
        print(f"No se pudo abrir {args.port}: {e}", file=sys.stderr)
        return 1

    print(f"Escuchando {args.port} ({args.baud}) -> {args.api}")
    while True:
        raw = ser.readline()
        if not raw:
            continue
        line = raw.decode("utf-8", errors="replace").strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("evento") == "no_match":
            print("(Arduino) sin coincidencia en memoria del sensor")
            continue
        eid = obj.get("estudiante_id")
        if eid is None:
            continue
        try:
            api_resp = post_asistencia(args.api, eid, obj.get("confianza"))
            nombre = None
            if isinstance(api_resp, dict):
                est = api_resp.get("estudiante")
                if isinstance(est, dict):
                    nombre = est.get("nombre")
            enviar_nombre_lcd(ser, nombre)
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8", errors="replace")
            print(f"HTTP {e.code}: {err}", file=sys.stderr)
        except urllib.error.URLError as e:
            print(f"Red/API: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
