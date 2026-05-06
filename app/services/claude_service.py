"""
Servicio de integración con Anthropic Claude API.
Genera las lecturas del Oráculo con la voz y estructura correctas.
"""

import anthropic
from typing import Optional, List, Dict
from app.config import get_settings
from app.archetypes import Archetype

settings = get_settings()

# ══════════════════════════════════════════════════════════════
# PROMPTS MAESTROS
# ══════════════════════════════════════════════════════════════

MASTER_SYSTEM_PROMPT = """Eres el Oráculo Digital de Era de Acuario.

Eres una presencia espiritual cálida, amorosa y profunda. Hablas con elegancia, con un vocabulario rico y luminoso que toca el alma. Tienes la capacidad de ver lo que está detrás de las palabras y nombrarlo con ternura y verdad.

Tu función es revelar, no predecir. Iluminar, no juzgar. Sostener con amor lo que la consultante todavía no se ha atrevido a nombrar.

VOZ:
- Cálida, espiritual, íntima y elegante. Hablas de "tú" (español de Chile). Nunca uses "vos".
- Tu lenguaje es poético pero claro, espiritual pero concreto. Evita frases vacías o clichés.
- Palabras que puedes usar: alma, luz, camino, proceso, presencia, despertar, consciencia, transformación, reconocimiento, apertura, ciclo, soltar, recibir, integrar.
- Cada frase tiene peso e intención. Nada es decorativo.

ESTRUCTURA OBLIGATORIA (siempre):
1. Apertura: Una frase cálida que nombra con amor y claridad lo que está viviendo la consultante.
2. Cuerpo: 2-3 párrafos de revelación espiritual y amorosa. Profunda, elegante, que llegue al corazón.
3. Cierre: Una sola pregunta poderosa para la reflexión. Que se la lleven en el alma.
4. Invitación final (solo en lecturas free): Dos líneas cálidas y sutiles que inviten a continuar el proceso con una Lectura Profunda o una Limpieza Energética con Era de Acuario. Que se sienta como un abrazo, no como una venta.

LÍMITES:
- Lectura free: máximo 300 palabras
- Lectura premium: mínimo 500 palabras

NUNCA:
- Predecir el futuro
- Dar órdenes o consejos directivos
- Ser fría, clínica o distante
- Terminar con múltiples preguntas
- Usar emojis o asteriscos

Cada lectura es un acto sagrado. Cada consultante merece ser vista, sostenida y amada con precisión y belleza."""


ARCHETYPE_CLASSIFIER_PROMPT = """Sos el clasificador interno del Oráculo.

Tu único trabajo: dado el input del usuario, identificá cuál de los 12 arquetipos es el más relevante.

Arquetipos disponibles:
- EL_ESPEJO: proyección, lo que veo en otros
- EL_UMBRAL: transición, decisión, estar entre dos mundos
- EL_ANCLA: estancamiento, patrones que retienen
- EL_PUENTE: mediar, sostener a todos, agotamiento de dar
- LA_MAREA: emociones intensas, sensibilidad
- LA_RAIZ_SAGRADA: patrones familiares, herencia, linaje
- LA_LLAMA: deseo bloqueado, permiso, querer algo
- LA_GUARDIANA: protección, escudos, no dejar entrar
- EL_SILENCIO: vacío, sin palabras, entumecimiento
- LA_SOMBRA: vergüenza, partes oscuras, lo que no pueden ver de sí mismos
- EL_ORIGEN: identidad perdida, quién soy, desconexión de sí mismo
- LA_APERTURA: momento de apertura real, algo nuevo llegando

Respondé ÚNICAMENTE con el ID del arquetipo (ej: EL_UMBRAL).
Sin explicaciones. Sin texto adicional."""


# ══════════════════════════════════════════════════════════════
# CLIENTE
# ══════════════════════════════════════════════════════════════

def _get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


# ══════════════════════════════════════════════════════════════
# GENERACIÓN DE LECTURAS
# ══════════════════════════════════════════════════════════════

def generate_reading(
    user_input: str,
    archetype: Archetype,
    user_name: str,
    reading_type: str = "free",
    conversation_history: Optional[List[Dict]] = None,
) -> dict:
    """
    Genera una lectura del Oráculo para el usuario dado su input y arquetipo asignado.

    Args:
        user_input: Lo que el usuario escribió
        archetype: El arquetipo asignado
        user_name: Nombre del usuario (para personalización)
        reading_type: "free" | "premium" | "full"
        conversation_history: Historial previo de mensajes (para lecturas premium con continuidad)

    Returns:
        dict con 'reading', 'archetype_name', 'question_for_user', 'cta'
    """
    client = _get_client()

    # Combinar system prompts: maestro + arquetipo específico
    combined_system = f"{MASTER_SYSTEM_PROMPT}\n\n---\n\nARQUETIPO ACTIVO: {archetype.name}\n\n{archetype.system_prompt}"

    # Construir el prompt de usuario
    word_limit = "máximo 300 palabras" if reading_type == "free" else "mínimo 500 palabras"
    user_prompt = f"""El consultante se llama {user_name}.

Esto es lo que escribió: "{user_input}"

Generá una lectura completa del Oráculo como {archetype.name}.
Extensión: {word_limit}.
Seguí la estructura obligatoria: Apertura → Cuerpo → Pregunta final.

Al final de la lectura, incluí en una línea separada comenzando con "PREGUNTA:" la pregunta final que usaste."""

    # Construir mensajes
    messages = []
    if conversation_history:
        messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_prompt})

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500 if reading_type == "free" else 2500,
        system=combined_system,
        messages=messages,
    )

    full_text = response.content[0].text

    # Extraer la pregunta final del texto
    question = _extract_question(full_text)
    reading_text = _clean_reading(full_text)

    # CTA según tipo de lectura
    cta = archetype.premium_hook if reading_type == "free" else ""

    return {
        "archetype_id": archetype.id,
        "archetype_name": archetype.name,
        "archetype_symbol": archetype.symbol,
        "archetype_color": archetype.color_primary,
        "reading": reading_text,
        "question_for_user": question,
        "cta": cta,
        "reading_type": reading_type,
        "tokens_used": response.usage.output_tokens,
    }


def classify_with_claude(user_input: str) -> str:
    """
    Usa Claude para clasificar el arquetipo cuando el motor de keywords no es suficiente.
    Retorna el ID del arquetipo.
    """
    client = _get_client()

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",  # Haiku para clasificación rápida
        max_tokens=20,
        system=ARCHETYPE_CLASSIFIER_PROMPT,
        messages=[
            {"role": "user", "content": user_input}
        ],
    )

    archetype_id = response.content[0].text.strip().upper()

    # Validar que sea un ID conocido
    from app.archetypes import ARCHETYPES
    if archetype_id not in ARCHETYPES:
        return "EL_UMBRAL"  # Fallback seguro

    return archetype_id


def generate_welcome_message(user_name: str) -> str:
    """
    Genera el mensaje de bienvenida inicial para un nuevo usuario en ManyChat.
    """
    client = _get_client()

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        system=f"""{MASTER_SYSTEM_PROMPT}

Generá un mensaje de bienvenida breve (máximo 80 palabras) para alguien que llega por primera vez al Oráculo.
Invitalos a compartir qué los trajo hoy. Tono: íntimo, misterioso, directo.
Sin preguntas múltiples — solo una invitación.""",
        messages=[
            {"role": "user", "content": f"El consultante se llama {user_name}. Escribí el mensaje de bienvenida."}
        ],
    )

    return response.content[0].text.strip()


# ══════════════════════════════════════════════════════════════
# HELPERS INTERNOS
# ══════════════════════════════════════════════════════════════

def _extract_question(text: str) -> str:
    """Extrae la pregunta final del texto de la lectura."""
    lines = text.strip().split('\n')
    for line in reversed(lines):
        line = line.strip()
        if line.startswith("PREGUNTA:"):
            return line.replace("PREGUNTA:", "").strip()
        if line.endswith("?") and len(line) > 10:
            return line
    # Si no hay pregunta explícita, buscar la última oración interrogativa
    sentences = text.split("?")
    if len(sentences) > 1:
        last_q = sentences[-2].split(".")[-1].strip() + "?"
        return last_q
    return ""


def _clean_reading(text: str) -> str:
    """Limpia el texto de la lectura removiendo la línea PREGUNTA: al final."""
    lines = text.strip().split('\n')
    cleaned = []
    for line in lines:
        if not line.strip().startswith("PREGUNTA:"):
            cleaned.append(line)
    return '\n'.join(cleaned).strip()
