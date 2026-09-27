"""
SMIP - Aplicación web académica.
Punto de entrada: FastAPI + Uvicorn.
Fase 3: envío de correos vía SendGrid API.
"""
import os
import pathlib
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
from contextlib import asynccontextmanager as _ac

from app.schemas import EmailSendRequest
from app.messages import guardar_mensaje, obtener_mensajes
from app.supabase_storage import (
    upload_file as s3_upload_file,
    list_files as s3_list_files,
    download_file as s3_download_file,
)

# Cargar variables de entorno desde .env si existe
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

logger = __import__("logging").getLogger("SMIP")
logger.setLevel(__import__("logging").INFO)
if not logger.handlers:
    h = __import__("logging").StreamHandler()
    h.setFormatter(__import__("logging").Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(h)

app = FastAPI(
    title="SMIP",
    description="Aplicación web académica - Fase 3",
    version="0.3.0",
)

# Monta carpeta static para CSS y JS
app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static",
)

# Directorio de archivos subidos (absoluto, resuelto en runtime)
UPLOAD_DIR = pathlib.Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Límite de tamaño para subida (10 MB)
MAX_UPLOAD_SIZE = 10 * 1024 * 1024

# Nombres de archivo no permitidos
FORBIDDEN_NAMES = frozenset({
    ".", "..", ".gitignore", ".env", "nul", "con", "prn",
    "aux", "com1", "com2", "com3", "com4", "com5",
    "lpt1", "lpt2", "lpt3", "lpt4", "lpt5",
    "com6", "com7", "com8", "com9",
    "lpt6", "lpt7", "lpt8", "lpt9",
})


def _safe_filename(filename: str) -> str:
    """
    Sanitiza el nombre de archivo:
    - Usa solo la parte final del path (evita path traversal).
    - Rechaza nombres reservados del sistema.
    - Neutraliza secuencias peligrosas.
    - Elimina caracteres no permitidos.
    """
    import unicodedata

    if not filename or not filename.strip():
        return ""

    # Normalizar unicode (NFC)
    filename = unicodedata.normalize("NFC", filename)

    # Extraer solo el nombre base (evita ../../etc/passwd)
    safe = pathlib.PurePosixPath(filename).name
    safe = pathlib.PureWindowsPath(filename).name

    # Neutralizar null bytes y secuencias de directorio
    safe = safe.replace("\x00", "").replace("%00", "")
    safe = safe.replace("../", "").replace("..\\", "")
    safe = safe.replace("/", "").replace("\\", "")

    # Quitar caracteres no permitidos (solo alfanuméricos, guion, punto, guión bajo)
    safe = "".join(c for c in safe if c.isalnum() or c in "._- ")

    # Quitar espacios al inicio/final y colapsar espacios internos
    safe = " ".join(safe.split())

    if not safe:
        return ""

    # Bajogelowcase para consistencia
    safe = safe.lower()

    # Rechazar nombres reservados
    if safe in FORBIDDEN_NAMES:
        return ""

    return safe


def _safe_path(filename: str) -> pathlib.Path:
    """Construye la ruta absoluta segura para un archivo dentro de uploads/."""
    safe = _safe_filename(filename)
    if not safe:
        raise ValueError(f"Nombre de archivo no válido: {filename!r}")

    dest = (UPLOAD_DIR / safe).resolve()
    if not dest.is_relative_to(UPLOAD_DIR.resolve()):
        raise ValueError(f"Path traversal detectado: {filename!r}")

    return dest


def _get_sendgrid_env() -> tuple[str, str, str]:
    """Lee y valida las variables de entorno de SendGrid."""
    api_key = os.environ.get("SENDGRID_API_KEY", "").strip()
    sender = os.environ.get("SENDGRID_FROM_EMAIL", "").strip()
    sender_name = os.environ.get("SENDGRID_FROM_NAME", "").strip() or "SMIP"
    return api_key, sender, sender_name


def _build_email_payload(to: str, subject: str, message: str, sender: str, sender_name: str) -> dict:
    """Construye el payload JSON para la API de SendGrid."""
    return {
        "personalizations": [
            {
                "to": [{"email": to}],
            }
        ],
        "from": {
            "email": sender,
            "name": sender_name,
        },
        "subject": subject,
        "content": [
            {
                "type": "text/plain",
                "value": message,
            }
        ],
    }


@app.get("/")
async def index(request: Request):
    """Página principal con el formulario de envío de correo (Fase 3)."""
    env = Environment(
        loader=FileSystemLoader("app/templates"),
        autoescape=True,
    )
    template = env.get_template("index.html")
    html = template.render(request=request)
    return HTMLResponse(content=html, status_code=200)


@app.get("/health")
async def health():
    """Endpoint de salud: devuelve OK para verificación externa."""
    return {"status": "ok", "service": "SMIP", "phase": 3}


@ app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Recibe un archivo multipart y lo guarda en Supabase Storage."""
    if not file.filename:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "No se proporcionó archivo."},
        )

    filename = _safe_filename(file.filename)
    if not filename:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "Nombre de archivo no válido."},
        )

    dest = _safe_path(filename)

    # Leer contenido y validar tamaño antes de escribir
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        return JSONResponse(
            status_code=413,
            content={
                "ok": False,
                "error": f"El archivo excede el límite de {MAX_UPLOAD_SIZE // (1024*1024)} MB.",
            },
        )

    # Subir a Supabase Storage en lugar de guardar localmente
    try:
        result = s3_upload_file(content, filename)
        return JSONResponse(
            status_code=200,
            content={
                "ok": True,
                "name": result["filename"],
                "size": result["size"],
                "download_url": result["download_url"],
                "path": str(dest),
            },
        )
    except Exception as e:
        logger.exception("Error al subir archivo a Supabase Storage.")
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "message": "Error al subir archivo a Supabase Storage.",
            },
        )


@ app.get("/files")
async def list_files():
    """Devuelve el listado de archivos almacenados en Supabase Storage."""
    try:
        files = s3_list_files()
        return {"files": files}
    except Exception as e:
        logger.exception("Error al listar archivos de Supabase Storage.")
        return {"files": []}


@ app.get("/download/{filename}")
async def download_file(filename: str):
    """Descarga un archivo desde Supabase Storage."""
    safe_name = _safe_filename(filename)
    if not safe_name:
        raise HTTPException(status_code=400, detail="Nombre de archivo no válido.")

    # Intentar descargar de Supabase Storage
    try:
        content = s3_download_file(safe_name)
        return Response(
            content=content,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{safe_name}"',
            },
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")
    except Exception as e:
        logger.exception(f"Error al descargar archivo '{safe_name}' de Supabase Storage.")
        raise HTTPException(status_code=500, detail="Error al descargar el archivo.")


@_ac
async def lifespan(app: FastAPI):
    """Hook de inicio/apagado de la aplicación FastAPI."""
    logger.info("SMIP iniciado (Fase 3).")
    yield
    logger.info("SMIP apagado.")


# ---------------------------------------------------------------------------
# Envío de correos vía SendGrid API (Fase 3)
# ---------------------------------------------------------------------------

@app.post("/send-email")
async def send_email(payload: EmailSendRequest):
    """
    Envía un correo electrónico mediante la API de SendGrid.
    Requiere las variables de entorno SENDGRID_API_KEY y SENDGRID_FROM_EMAIL.
    """
    api_key, sender, sender_name = _get_sendgrid_env()

    if not api_key:
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "message": "SendGrid no configurado: falta SENDGRID_API_KEY.",
            },
        )

    if not sender:
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "message": "SendGrid no configurado: falta SENDGRID_FROM_EMAIL.",
            },
        )

    payload_data = _build_email_payload(
        to=payload.to,
        subject=payload.subject,
        message=payload.message,
        sender=sender,
        sender_name=sender_name,
    )

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload_data,
            )

            if response.status_code == 202:
                # Guardar en historial
                guardar_mensaje(
                    to=payload.to,
                    subject=payload.subject,
                    message=payload.message,
                    success=True,
                )
                return JSONResponse(
                    status_code=200,
                    content={
                        "ok": True,
                        "message": "Correo enviado correctamente.",
                    },
                )
            else:
                # Error de API: no revelar detalles Internos
                logger.error(
                    "SendGrid API error: %s %s",
                    response.status_code,
                    response.text,
                )
                return JSONResponse(
                    status_code=500,
                    content={
                        "ok": False,
                        "message": f"Error al enviar el correo (código {response.status_code}).",
                    },
                )

    except httpx.ConnectError:
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "message": "No se pudo conectar a SendGrid. Verifica la red.",
            },
        )

    except httpx.TimeoutException:
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "message": "Tiempo de espera agotado al conectar con SendGrid.",
            },
        )

    except Exception:
        logger.exception("Error inesperado al enviar correo.")
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "message": "Error interno al enviar el correo.",
            },
        )


@app.get("/messages")
async def get_messages():
    """Devuelve el historial de mensajes enviados."""
    return {"messages": obtener_mensajes()}


@app.get("/messages/clear")
async def clear_messages():
    """Limpia el historial de mensajes."""
    count = limpiar_historial()
    return {"ok": True, "cleared": count}
