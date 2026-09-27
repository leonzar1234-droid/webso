r"""
SMIP — Pruebas automatizadas Fase 3 (envío de correo vía SendGrid).

Correr con:
    cd C:\Users\tulio\SMIP
    .\.venv\Scripts\activate
    python -m pytest app/test_email.py -v

No se envían correos reales: se usa mocking de httpx para simular
la API de SendGrid.
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import httpx
import pytest
from pydantic import EmailStr

from app.main import app
from app.schemas import EmailSendRequest
from fastapi.testclient import TestClient

client = TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_payload(**overrides):
    payload = {
        "to": "destinatario@example.com",
        "subject": "Asunto de prueba",
        "message": "Este es el cuerpo del mensaje.",
    }
    payload.update(overrides)
    return payload


def _configurar_sendgrid_vars(monkeypatch=None):
    """Configura variables de SendGrid de prueba."""
    if monkeypatch is not None:
        monkeypatch.setenv("SENDGRID_API_KEY", "SG.test-api-key-12345")
        monkeypatch.setenv("SENDGRID_FROM_EMAIL", "remitente@test.local")
        monkeypatch.setenv("SENDGRID_FROM_NAME", "SMIP Test")
    else:
        os.environ["SENDGRID_API_KEY"] = "SG.test-api-key-12345"
        os.environ["SENDGRID_FROM_EMAIL"] = "remitente@test.local"
        os.environ["SENDGRID_FROM_NAME"] = "SMIP Test"


class _MockSendGridClient:
    """Mock de httpx.AsyncClient que soporta async with y post()."""

    def __init__(self, response_status=202, response_text=""):
        self._response_status = response_status
        self._response_text = response_text
        self.call_args = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, *args, **kwargs):
        self.call_args = (args, kwargs)
        mock_response = MagicMock()
        mock_response.status_code = self._response_status
        mock_response.text = self._response_text
        mock_response.__await__ = lambda self: iter([self])
        return mock_response


def _mock_sendgrid_request(monkeypatch, response_status=202, response_text=""):
    """Mockea httpx.AsyncClient.post para simular la API de SendGrid."""
    mock_client = _MockSendGridClient(response_status, response_text)
    monkeypatch.setattr(httpx, "AsyncClient", MagicMock(return_value=mock_client))
    return mock_client


# ---------------------------------------------------------------------------
# Validación del modelo (Pydantic)
# ---------------------------------------------------------------------------

def test_valid_payload_es_aceptado():
    """Payload válido es aceptado por Pydantic (puede fallar en envío)."""
    resp = client.post("/send-email", json=_valid_payload())
    assert resp.status_code in (200, 500)


def test_rechaza_to_invalid():
    """to no es un email válido -> 422."""
    resp = client.post("/send-email", json=_valid_payload(to="no-es-un-email"))
    assert resp.status_code == 422


def test_rechaza_to_invalido():
    """to vacío -> 422."""
    resp = client.post("/send-email", json=_valid_payload(to=""))
    assert resp.status_code == 422


def test_rechaza_subject_vacio():
    """subject vacío -> 422."""
    resp = client.post("/send-email", json=_valid_payload(subject=""))
    assert resp.status_code == 422


def test_rechaza_message_vacio():
    """message vacío -> 422."""
    resp = client.post("/send-email", json=_valid_payload(message=""))
    assert resp.status_code == 422


def test_rechaza_payload_incompleto():
    """Payload incompleto -> 422."""
    resp = client.post("/send-email", json={})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Comportamiento sin SendGrid configurado
# ---------------------------------------------------------------------------

def test_sin_configuracion_retorna_500():
    """Cuando faltan variables de SendGrid, el endpoint responde 500."""
    for var in ("SENDGRID_API_KEY", "SENDGRID_FROM_EMAIL", "SENDGRID_FROM_NAME"):
        os.environ.pop(var, None)
    resp = client.post("/send-email", json=_valid_payload())
    assert resp.status_code == 500
    data = resp.json()
    assert "SG." not in str(data)
    assert data.get("ok") is False


# ---------------------------------------------------------------------------
# Mocking de SendGrid: envío exitoso
# ---------------------------------------------------------------------------

def test_envio_exitoso_con_mock(monkeypatch):
    """Simula envío vía SendGrid exitoso. Verifica 200 sin filtrar API key."""
    _configurar_sendgrid_vars(monkeypatch)
    mock_client = _mock_sendgrid_request(monkeypatch, 202)

    resp = client.post("/send-email", json=_valid_payload())
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "SG.test-api-key-12345" not in str(data)
    assert mock_client.call_args is not None


def test_sendgrid_api_call_con_correcto_payload(monkeypatch):
    """Verifica que se llama a la API de SendGrid con el payload correcto."""
    _configurar_sendgrid_vars(monkeypatch)

    captured_json = {}

    async def capture_post(*args, **kwargs):
        captured_json.update(kwargs.get("json", {}))
        mock_resp = MagicMock()
        mock_resp.status_code = 202
        mock_resp.__await__ = lambda self: iter([self])
        return mock_resp

    mock_client = MagicMock()
    mock_client.__aenter__ = capture_post
    mock_client.__aexit__ = MagicMock(return_value=None)

    monkeypatch.setattr(httpx, "AsyncClient", MagicMock(return_value=mock_client))

    resp = client.post("/send-email", json=_valid_payload(
        to="destinatario@example.com",
        subject="Asunto Test",
        message="Mensaje de prueba",
    ))
    assert resp.status_code == 200

    assert "personalizations" in captured_json
    assert captured_json["personalizations"][0]["to"][0]["email"] == "destinatario@example.com"
    assert captured_json["from"]["email"] == "remitente@test.local"
    assert captured_json["from"]["name"] == "SMIP Test"
    assert captured_json["subject"] == "Asunto Test"
    assert captured_json["content"][0]["value"] == "Mensaje de prueba"


def test_respuesta_nunca_incluye_api_key(monkeypatch):
    """Incluso en caso de error, la API key no debe filtrarse."""
    _configurar_sendgrid_vars(monkeypatch)

    mock_client = MagicMock()
    mock_client.__aenter__ = MagicMock(return_value=mock_client)
    mock_client.__aexit__ = MagicMock(return_value=None)
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_response.__await__ = lambda self: iter([self])
    mock_client.post = MagicMock(return_value=mock_response)

    monkeypatch.setattr(httpx, "AsyncClient", MagicMock(return_value=mock_client))

    resp = client.post("/send-email", json=_valid_payload())
    assert resp.status_code == 500
    data = resp.json()
    assert data.get("ok") is False
    assert "SG.test-api-key-12345" not in str(data)


def test_error_sendgrid_api_no_revela_detalles(monkeypatch):
    """Error de la API de SendGrid no revela detalles Internos."""
    _configurar_sendgrid_vars(monkeypatch)

    mock_client = MagicMock()
    mock_client.__aenter__ = MagicMock(return_value=mock_client)
    mock_client.__aexit__ = MagicMock(return_value=None)
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = '{"errors":[{"field":"authorization","message":"Invalid API Key"}]}'
    mock_response.__await__ = lambda self: iter([self])
    mock_client.post = MagicMock(return_value=mock_response)

    monkeypatch.setattr(httpx, "AsyncClient", MagicMock(return_value=mock_client))

    resp = client.post("/send-email", json=_valid_payload())
    assert resp.status_code == 500
    data = resp.json()
    assert data.get("ok") is False
    assert "Invalid API Key" not in str(data)


# ---------------------------------------------------------------------------
# Errores de red
# ---------------------------------------------------------------------------

def test_error_conexion_red(monkeypatch):
    """Error de conexión a SendGrid devuelve mensaje apropiado."""
    _configurar_sendgrid_vars(monkeypatch)

    async def raise_connect_error(*args, **kwargs):
        raise httpx.ConnectError("Connection refused")

    mock_client = MagicMock()
    mock_client.__aenter__ = raise_connect_error
    mock_client.__aexit__ = MagicMock(return_value=None)

    monkeypatch.setattr(httpx, "AsyncClient", MagicMock(return_value=mock_client))

    resp = client.post("/send-email", json=_valid_payload())
    assert resp.status_code == 500
    data = resp.json()
    assert data["ok"] is False
    assert "No se pudo conectar a SendGrid" in data["message"]


def test_timeout_sendgrid(monkeypatch):
    """Timeout al conectar con SendGrid devuelve mensaje apropiado."""
    _configurar_sendgrid_vars(monkeypatch)

    async def raise_timeout(*args, **kwargs):
        raise httpx.TimeoutException("Timeout")

    mock_client = MagicMock()
    mock_client.__aenter__ = raise_timeout
    mock_client.__aexit__ = MagicMock(return_value=None)

    monkeypatch.setattr(httpx, "AsyncClient", MagicMock(return_value=mock_client))

    resp = client.post("/send-email", json=_valid_payload())
    assert resp.status_code == 500
    data = resp.json()
    assert data["ok"] is False
    assert "Tiempo de espera" in data["message"]


# ---------------------------------------------------------------------------
# Compatibilidad: Fase 2 sigue funcionando
# ---------------------------------------------------------------------------

def test_phases_1_y_2_siguen_funcionando():
    """Verificar que las fases anteriores no se rompieron."""
    # Fase 1 - página principal
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "SMIP" in resp.text

    # Fase 1 - health
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["phase"] == 3

    # Fase 2 - listado de archivos
    resp = client.get("/files")
    assert resp.status_code == 200
    assert "files" in resp.json()

    # Fase 2 - path traversal rechazado
    resp = client.get("/download/../fuera.txt")
    assert resp.status_code in (400, 404)
