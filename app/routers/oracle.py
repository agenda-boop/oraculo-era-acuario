"""
Router principal del Oráculo.
Endpoints para lecturas y consulta de arquetipos.
"""

import uuid
import time
from fastapi import APIRouter, HTTPException, Depends
from app.models import (
    OracleReadingRequest,
    OracleReadingResponse,
    ArchetypeInfo,
    ArchetypeListResponse,
)
from app.archetype_engine import classify_archetype
from app.services.claude_service import generate_reading, classify_with_claude
from app.archetypes import get_archetype, get_archetype_list, ARCHETYPES
from app.config import get_settings

router = APIRouter(prefix="/oracle", tags=["Oracle"])
settings = get_settings()

CONFIDENCE_THRESHOLD = 0.4  # Si confianza < threshold, usar Claude para clasificar


@router.post("/reading", response_model=OracleReadingResponse)
async def create_reading(request: OracleReadingRequest):
    """
    Genera una lectura completa del Oráculo.

    1. Clasifica el arquetipo según el input del usuario
    2. Genera la lectura con Claude usando el system_prompt del arquetipo
    3. Retorna lectura, pregunta final y CTA
    """
    start_time = time.time()

    # 1. Clasificar arquetipo
    if request.force_archetype and settings.app_env == "development":
        # Solo en desarrollo se puede forzar el arquetipo
        archetype_id = request.force_archetype.upper()
        archetype = get_archetype(archetype_id)
        if not archetype:
            raise HTTPException(status_code=400, detail=f"Arquetipo '{archetype_id}' no existe")
        confidence = 1.0
        classification_method = "forced"
    else:
        # Clasificación por keywords
        classification = classify_archetype(request.input_text)

        # Si la confianza es baja, usar Claude para refinar
        if classification.confidence < CONFIDENCE_THRESHOLD:
            archetype_id = classify_with_claude(request.input_text)
            archetype = get_archetype(archetype_id)
            confidence = 0.6  # Confianza media cuando Claude clasifica
            classification_method = "claude_classifier"
        else:
            archetype = classification.archetype
            confidence = classification.confidence
            classification_method = classification.method

    if not archetype:
        raise HTTPException(status_code=500, detail="Error al clasificar arquetipo")

    # 2. Generar sesión
    session_id = request.session_id or str(uuid.uuid4())

    # 3. Generar lectura con Claude
    try:
        reading_data = generate_reading(
            user_input=request.input_text,
            archetype=archetype,
            user_name=request.user_name,
            reading_type=request.reading_type.value,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Error generando lectura: {str(e)}")

    elapsed = round(time.time() - start_time, 2)

    return OracleReadingResponse(
        session_id=session_id,
        archetype=ArchetypeInfo(
            id=archetype.id,
            name=archetype.name,
            symbol=archetype.symbol,
            color_primary=archetype.color_primary,
            essence=archetype.essence,
        ),
        reading=reading_data["reading"],
        question_for_user=reading_data["question_for_user"],
        cta=reading_data["cta"],
        reading_type=request.reading_type.value,
        confidence=confidence,
        classification_method=classification_method,
    )


@router.get("/archetypes", response_model=ArchetypeListResponse)
async def list_archetypes():
    """Lista todos los arquetipos disponibles."""
    archetypes_raw = get_archetype_list()
    archetypes = [
        ArchetypeInfo(
            id=a["id"],
            name=a["name"],
            symbol=a["symbol"],
            color_primary=a["color_primary"],
            essence=a["essence"],
        )
        for a in archetypes_raw
    ]
    return ArchetypeListResponse(archetypes=archetypes, total=len(archetypes))


@router.get("/archetypes/{archetype_id}", response_model=ArchetypeInfo)
async def get_archetype_detail(archetype_id: str):
    """Obtiene detalle de un arquetipo específico."""
    archetype = get_archetype(archetype_id.upper())
    if not archetype:
        raise HTTPException(status_code=404, detail=f"Arquetipo '{archetype_id}' no encontrado")
    return ArchetypeInfo(
        id=archetype.id,
        name=archetype.name,
        symbol=archetype.symbol,
        color_primary=archetype.color_primary,
        essence=archetype.essence,
    )


@router.post("/classify")
async def classify_input(data: dict):
    """
    Clasifica un input y retorna el arquetipo asignado + scores (útil para debug).
    """
    user_input = data.get("input", "")
    if not user_input:
        raise HTTPException(status_code=400, detail="Campo 'input' requerido")

    result = classify_archetype(user_input)
    top_3 = sorted(result.scores.items(), key=lambda x: x[1], reverse=True)[:3]

    return {
        "archetype_id": result.archetype_id,
        "archetype_name": result.archetype.name,
        "confidence": result.confidence,
        "method": result.method,
        "top_3": [{"id": k, "score": v} for k, v in top_3],
    }
