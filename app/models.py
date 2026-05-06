"""
Modelos Pydantic para request/response de la API del Oráculo.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from enum import Enum


class ReadingType(str, Enum):
    FREE = "free"
    PREMIUM = "premium"
    FULL = "full"


# ── Requests ──────────────────────────────────────────────────

class OracleReadingRequest(BaseModel):
    user_id: Optional[str] = Field(None, description="ID único del usuario")
    user_name: str = Field(..., description="Nombre del usuario para personalización")
    input_text: str = Field(..., min_length=5, max_length=2000, description="Lo que el usuario quiere consultar")
    session_id: Optional[str] = Field(None, description="ID de sesión existente (para continuidad)")
    reading_type: ReadingType = Field(ReadingType.FREE, description="Tipo de lectura")
    force_archetype: Optional[str] = Field(None, description="Forzar arquetipo específico (solo para testing)")


class ManyChatWebhookRequest(BaseModel):
    subscriber_id: str
    first_name: str
    last_name: Optional[str] = ""
    gender: Optional[str] = ""
    locale: Optional[str] = "es"
    message_text: str
    flow_ns: Optional[str] = None
    custom_fields: Optional[dict] = {}


class UserCreateRequest(BaseModel):
    instagram_id: str
    first_name: str
    last_name: Optional[str] = ""
    email: Optional[str] = None


# ── Responses ─────────────────────────────────────────────────

class ArchetypeInfo(BaseModel):
    id: str
    name: str
    symbol: str
    color_primary: str
    essence: str


class OracleReadingResponse(BaseModel):
    session_id: str
    archetype: ArchetypeInfo
    reading: str
    question_for_user: str
    cta: str
    reading_type: str
    confidence: float
    classification_method: str


class ManyChatResponse(BaseModel):
    """Formato de respuesta compatible con ManyChat Dynamic Content."""
    version: str = "v2"
    content: dict


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str


class ArchetypeListResponse(BaseModel):
    archetypes: List[ArchetypeInfo]
    total: int
