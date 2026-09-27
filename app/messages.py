"""Historial de mensajes para SMIP - Fase 3.

Guarda los correos enviados en un archivo JSON para que se puedan
ver en la interfaz web.
"""
import json
import pathlib
import datetime
from typing import Any

# Archivo donde se guardan los mensajes
MESSAGES_FILE = pathlib.Path(__file__).resolve().parent.parent / "messages.json"


def guardar_mensaje(to: str, subject: str, message: str, success: bool) -> dict[str, Any]:
    """Guarda un mensaje en el historial."""
    MESSAGES_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Cargar mensajes existentes
    mensajes = []
    if MESSAGES_FILE.exists():
        try:
            with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
                mensajes = json.load(f)
        except (json.JSONDecodeError, OSError):
            mensajes = []

    # Agregar nuevo mensaje
    nuevo = {
        "to": to,
        "subject": subject,
        "message": message,
        "success": success,
        "timestamp": datetime.datetime.now().isoformat(),
    }
    mensajes.append(nuevo)

    # Guardar
    with open(MESSAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(mensajes, f, indent=2, ensure_ascii=False)

    return nuevo


def obtener_mensajes() -> list[dict[str, Any]]:
    """Obtiene el historial de mensajes."""
    if not MESSAGES_FILE.exists():
        return []

    try:
        with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def limpiar_historial() -> int:
    """Limpia el historial y devuelve la cantidad de mensajes eliminados."""
    if not MESSAGES_FILE.exists():
        return 0

    try:
        with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
            mensajes = json.load(f)
        count = len(mensajes)
        MESSAGES_FILE.unlink()
        return count
    except (json.JSONDecodeError, OSError):
        return 0
