"""
Envío de WhatsApp vía Twilio (cuando TWILIO_* está en .env).
Si faltan credenciales, solo se registra en consola (modo simulado).
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict


def normalizar_telefono_whatsapp(raw: str) -> str:
    """Solo dígitos; asume Colombia +57 si vienen 10 dígitos empezando en 3."""
    digits = re.sub(r"\D", "", (raw or "").strip())
    if not digits:
        return ""
    if digits.startswith("57") and len(digits) >= 12:
        return digits[:12]
    if len(digits) == 10 and digits[0] == "3":
        return "57" + digits
    return digits


def enviar_mensaje_whatsapp(telefono_solo_digitos: str, body: str) -> Dict[str, Any]:
    """
    telefono_solo_digitos: ej. 573178668782 (sin +).

    Devuelve siempre un dict con:
      - ok: bool (mensaje enviado por Twilio o simulado con éxito)
      - modo: 'twilio' | 'simulado' | 'error'
      - detalle: sid de Twilio, None en simulado, o texto de error
    """
    sid = (os.getenv("TWILIO_ACCOUNT_SID") or "").strip()
    token = (os.getenv("TWILIO_AUTH_TOKEN") or "").strip()
    from_wa = (os.getenv("TWILIO_WHATSAPP_FROM") or "").strip()

    if not (sid and token and from_wa):
        print(f"[WhatsApp simulado] → {telefono_solo_digitos}: {body}")
        return {"ok": True, "modo": "simulado", "detalle": None}

    try:
        from twilio.rest import Client

        client = Client(sid, token)
        to_wa = f"whatsapp:+{telefono_solo_digitos}"
        msg = client.messages.create(body=body, from_=from_wa, to=to_wa)
        return {"ok": True, "modo": "twilio", "detalle": msg.sid}
    except Exception as e:
        err = str(e)
        print(f"[WhatsApp Twilio] Error: {err}")
        return {"ok": False, "modo": "error", "detalle": err}
