"""
SMIP - Esquemas Pydantic para envío de correo (Fase 3).
"""
from pydantic import BaseModel, EmailStr, Field


class EmailSendRequest(BaseModel):
    """Payload validado para POST /send-email."""

    to: EmailStr = Field(
        ...,
        description="Dirección de correo del destinatario.",
    )
    subject: str = Field(
        ...,
        min_length=1,
        description="Asunto del correo.",
    )
    message: str = Field(
        ...,
        min_length=1,
        description="Cuerpo del mensaje.",
    )


class EmailSendResponse(BaseModel):
    """Respuesta del endpoint /send-email."""

    ok: bool
    message: str
