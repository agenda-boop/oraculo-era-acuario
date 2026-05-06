from typing import Optional, List, Dict
"""
Router para webhook de ManyChat.
Recibe mensajes de Instagram DM y retorna lecturas del Oráculo en formato ManyChat.
"""

import hashlib
import hmac
import uuid
from fastapi import APIRouter, HTTPException, Request, Header
from app.models import ManyChatWebhookRequest, ManyChatResponse
from app.archetype_engine import classify_archetype
from app.services.claude_service import generate_reading, classify_with_claude, generate_welcome_message
from app.archetypes import get_archetype
from app.config import get_settings

router = APIRouter(prefix="/webhook", tags=["ManyChat Webhook"])
settings = get_settings()


def _verify_manychat_signature(body: bytes, signature: str) -> bool:
    """Verifica la firma HMAC del webhook de ManyChat."""
    if not settings.manychat_webhook_secret:
        return True  # En desarrollo sin secret configurado
    expected = hmac.new(
        settings.manychat_webhook_secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature.replace("sha256=", ""))


@router.post("/manychat")
async def manychat_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256"),
):
    """
    Webhook principal para ManyChat.
    Recibe el input del usuario desde Instagram DM y retorna la lectura del Oráculo.
    Formato de respuesta: ManyChat Dynamic Content v2.
    """
    body = await request.body()

    # Verificar firma si está configurada
    if x_hub_signature_256 and settings.manychat_webhook_secret:
        if not _verify_manychat_signature(body, x_hub_signature_256):
            raise HTTPException(status_code=401, detail="Firma inválida")

    # Parsear body
    try:
        data = await request.json()
        payload = ManyChatWebhookRequest(**data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Payload inválido: {str(e)}")

    user_name = payload.first_name or "consultante"
    user_input = payload.message_text.strip()

    # Detectar si es saludo/inicio (mensaje muy corto o genérico)
    if _is_greeting(user_input):
        welcome = generate_welcome_message(user_name)
        return _manychat_response([
            {"type": "text", "text": welcome}
        ])

    # Clasificar arquetipo
    classification = classify_archetype(user_input)
    if classification.confidence < 0.4:
        archetype_id = classify_with_claude(user_input)
    else:
        archetype_id = classification.archetype_id

    archetype = get_archetype(archetype_id)
    if not archetype:
        archetype = get_archetype("EL_UMBRAL")

    # Generar lectura free
    reading_data = generate_reading(
        user_input=user_input,
        archetype=archetype,
        user_name=user_name,
        reading_type="free",
    )

    # Armar respuesta ManyChat (mensajes múltiples)
    messages = [
        {
            "type": "text",
            "text": f"*{archetype.symbol} {archetype.name}*"
        },
        {
            "type": "text",
            "text": reading_data["reading"]
        },
    ]

    # Agregar CTA si existe
    if reading_data.get("cta"):
        messages.append({
            "type": "text",
            "text": reading_data["cta"]
        })
        messages.append({
            "type": "cards",
            "elements": [
                {
                    "title": "Lectura Profunda",
                    "subtitle": "Accedé a tu lectura completa",
                    "image_url": "",
                    "buttons": [
                        {
                            "type": "url",
                            "caption": "Quiero mi Lectura Profunda →",
                            "url": "https://eradeacuariospa.com/lectura-profunda"
                        }
                    ]
                }
            ]
        })

    return _manychat_response(messages)


@router.post("/manychat/welcome")
async def manychat_welcome(request: Request):
    """Endpoint para mensaje de bienvenida inicial."""
    try:
        data = await request.json()
        user_name = data.get("first_name", "consultante")
    except Exception:
        user_name = "consultante"

    welcome = generate_welcome_message(user_name)
    return _manychat_response([{"type": "text", "text": welcome}])


# ── Helpers ──────────────────────────────────────────────────

def _is_greeting(text: str) -> bool:
    """Detecta si el mensaje es un saludo o inicio de conversación."""
    greetings = [
        "hola", "hi", "hey", "buenas", "buen dia", "buenos dias",
        "buenas tardes", "buenas noches", "inicio", "start", "empezar",
        "quiero consultar", "quiero una lectura", "activar"
    ]
    text_lower = text.lower().strip()
    return (
        len(text_lower) < 30 and
        any(g in text_lower for g in greetings)
    )


def _manychat_response(messages: List[Dict]) -> dict:
    """Construye la respuesta en formato ManyChat Dynamic Content v2."""
    return {
        "version": "v2",
        "content": {
            "messages": messages,
            "actions": [],
            "quick_replies": []
        }
    }
