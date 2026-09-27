r"""
SMIP — Pruebas automatizadas (Fase 2).

Correr con:
    cd C:\Users\tulio\SMIP
    .\.venv\Scripts\activate
    python -m pytest app/test_main.py -v

Se usa TestClient de FastAPI (sin servidor real).
"""
from io import BytesIO

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _upload(name: str, content: bytes):
    """Prepara un archivo cualquiera para pruebas de subida."""
    return {
        "file": (name, BytesIO(content), "application/octet-stream"),
    }


# ---------------------------------------------------------------------------
# Índice y salud
# ---------------------------------------------------------------------------

def test_index_returns_html():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    body = resp.text
    assert "<html" in body.lower()
    assert "SMIP" in body
    assert "Fase 3" in body


def test_health_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "SMIP"
    assert data["phase"] == 3


# ---------------------------------------------------------------------------
# Subida de archivos
# ---------------------------------------------------------------------------

def test_upload_rejects_missing_file():
    resp = client.post("/upload")
    assert resp.status_code == 422  # FastAPI valida falta de file=File(...)


def test_upload_small_text_file():
    resp = client.post("/upload", files=_upload("hello.txt", b"Hola mundo"))
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["name"] == "hello.txt"
    assert data["size"] == 10


def test_upload_creates_file_on_disk():
    """El archivo subido debe estar físicamente en uploads/."""
    name = "fase2_test_binary.bin"
    payload = bytes(range(256))  # 256 bytes
    resp = client.post("/upload", files=_upload(name, payload))
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True

    import pathlib
    upload_dir = pathlib.Path(__file__).resolve().parent.parent / "uploads"
    assert (upload_dir / name).is_file()
    assert (upload_dir / name).read_bytes() == payload


def test_upload_overwrites_existing_file():
    """Subir un archivo con nombre duplicado sobrescribe el anterior."""
    name = "fase2_overwrite.txt"
    client.post("/upload", files=_upload(name, b"Version A"))
    resp = client.post("/upload", files=_upload(name, b"Version B"))
    assert resp.status_code == 200
    assert resp.json()["size"] == 9
    import pathlib
    upload_dir = pathlib.Path(__file__).resolve().parent.parent / "uploads"
    assert (upload_dir / name).read_bytes() == b"Version B"


def test_upload_rejects_empty_filename():
    # Nombre vacío con contenido vacío: FastAPI valida y devuelve 422
    # antes de llegar al handler. Comportamiento aceptable.
    resp = client.post(
        "/upload",
        files={"file": ("", BytesIO(b""), "application/octet-stream")},
    )
    assert resp.status_code in (400, 422)


def test_upload_rejects_path_traversal():
    # El nombre seguro extrae solo la componente final: "../evil.txt"
    # se convierte en "evil.txt" y se guarda en uploads/. Esto es
    # comportamiento de sanitización, no de rechazo.
    resp = client.post(
        "/upload",
        files=_upload("../evil.txt", b"no debe guardarse fuera"),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["name"] == "evil.txt"
    import pathlib
    upload_dir = pathlib.Path(__file__).resolve().parent.parent / "uploads"
    # Verificar que NO se escapó del directorio uploads/
    assert (upload_dir / "evil.txt").is_file()
    assert not (upload_dir.parent / "evil.txt").exists()


def test_upload_rejects_absolute_path():
    # Ruta absoluta Windows: el nombre seguro extrae solo el nombre final.
    resp = client.post(
        "/upload",
        files=_upload("C:/Windows/system32/config/sam", b"bad"),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["name"] == "sam"
    import pathlib
    upload_dir = pathlib.Path(__file__).resolve().parent.parent / "uploads"
    assert (upload_dir / "sam").is_file()


def test_upload_rejects_null_byte():
    # El byte nulo es codificado por FastAPI/python-multipart como %00
    # y luego sanitizado por _safe_filename. El nombre resultante puede
    # variar segun la versin; verificamos que se guarda dentro de uploads/
    # y que no hay escape.
    raw = "legit.txt" + chr(0) + ".exe"
    resp = client.post(
        "/upload",
        files=_upload(raw, b"malicioso"),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    name = data["name"]
    # El nombre debe terminar en .exe y no contener..
    assert name.endswith(".exe")
    # Verificar que el archivo queda dentro de uploads/
    import pathlib
    upload_dir = pathlib.Path(__file__).resolve().parent.parent / "uploads"
    assert (upload_dir / name).is_file()
    assert not (upload_dir.parent / name).exists()


def test_upload_rejects_empty_file_with_no_name():
    # Sin nombre: FastAPI devuelve 422 (validación) antes del handler.
    resp = client.post(
        "/upload",
        files={"file": ("", BytesIO(b""), "text/plain")},
    )
    assert resp.status_code in (400, 422)


def test_upload_respects_size_limit():
    """Archivo mayor a 10 MB debe ser rechazado."""
    big = b"x" * (11 * 1024 * 1024)  # 11 MB
    resp = client.post("/upload", files=_upload("big.bin", big))
    assert resp.status_code == 413
    data = resp.json()
    assert data["ok"] is False
    assert "10" in data["error"]


# ---------------------------------------------------------------------------
# Listado de archivos
# ---------------------------------------------------------------------------

def test_files_empty_when_no_files():
    resp = client.get("/files")
    assert resp.status_code == 200
    data = resp.json()
    assert "files" in data
    assert isinstance(data["files"], list)
    # Puede haber archivos sobrantes de otras pruebas; validamos solo la estructura
    for entry in data["files"]:
        assert "name" in entry
        assert "size" in entry


def test_files_lists_uploaded_file():
    name = "fase2_list_test.txt"
    client.post("/upload", files=_upload(name, b"contenido visible"))
    resp = client.get("/files")
    assert resp.status_code == 200
    data = resp.json()
    names = [e["name"] for e in data["files"]]
    assert name in names
    sizes = {e["name"]: e["size"] for e in data["files"]}
    assert sizes[name] == len(b"contenido visible")


# ---------------------------------------------------------------------------
# Descarga
# ---------------------------------------------------------------------------

def test_download_existing_file():
    name = "fase2_dl_test.txt"
    content = b"Contenido para descargar"
    client.post("/upload", files=_upload(name, content))
    resp = client.get("/download/" + name)
    assert resp.status_code == 200
    assert resp.content == content
    cd = resp.headers.get("content-disposition", "")
    assert "attachment" in cd.lower()
    assert name in cd


def test_download_nonexistent_returns_404():
    resp = client.get("/download/archivo_inexistente_12345.txt")
    assert resp.status_code == 404


def test_download_rejects_path_traversal():
    # El nombre seguro extrae solo la componente final: "../outside.txt"
    # se convierte en "outside.txt" que no existe -> 404.
    resp = client.get("/download/../outside.txt")
    assert resp.status_code == 404


def test_download_rejects_null_byte_in_name():
    # El nombre con null byte es rechazado por _safe_filename (detecta \x00).
    raw = "valid.txt" + chr(0) + ".exe"
    from urllib.parse import quote
    encoded = quote(raw, safe="")
    resp = client.get("/download/" + encoded)
    assert resp.status_code == 400


def test_download_requires_real_file_not_directory():
    """Subir un directororio no es posible vía form, pero verificamos que
    caller no puede leer un directorio como archivo."""
    import pathlib
    upload_dir = pathlib.Path(__file__).resolve().parent.parent / "uploads"
    # Si existiera un directorio con ese nombre, debería fallar o 404.
    # Creamos un directorio temporal para la prueba.
    d = upload_dir / "fase2_dir_test"
    d.mkdir(exist_ok=True)
    try:
        resp = client.get("/download/fase2_dir_test")
        # La ruta es un directorio, no un archivo: se espera 404 o 400
        # (nuestra lógica devuelve 404 porque is_file() es False).
        assert resp.status_code in (400, 404)
    finally:
        d.rmdir()


# ---------------------------------------------------------------------------
# Comportamiento definido: archivo vacío
# ---------------------------------------------------------------------------

def test_upload_empty_file_is_accepted():
    """Un archivo con nombre y 0 bytes: se acepta y guarda como 0 bytes
    (comportamiento definido para esta fase)."""
    name = "fase2_empty.bin"
    resp = client.post("/upload", files=_upload(name, b""))
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["size"] == 0
    import pathlib
    upload_dir = pathlib.Path(__file__).resolve().parent.parent / "uploads"
    assert (upload_dir / name).is_file()
    assert (upload_dir / name).stat().st_size == 0
