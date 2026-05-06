"""
Motor de clasificación de arquetipos del Oráculo.
Asigna el arquetipo más afín al input del usuario con score de confianza.
"""

import re
from typing import Optional, List, Dict
from dataclasses import dataclass
from app.archetypes import ARCHETYPES, Archetype


@dataclass
class ClassificationResult:
    archetype_id: str
    archetype: Archetype
    confidence: float
    scores: Dict[str, float]
    method: str  # "keyword" | "semantic_fallback"


def _normalize(text: str) -> str:
    """Normaliza texto para comparación: minúsculas, sin puntuación extra."""
    text = text.lower().strip()
    # Reemplaza acentos comunes del español
    replacements = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'ü': 'u', 'ñ': 'n'
    }
    for accented, plain in replacements.items():
        text = text.replace(accented, plain)
    return text


def _keyword_score(text_normalized: str, keywords: List[str]) -> float:
    """
    Calcula score de coincidencia entre texto y lista de keywords.
    Palabras completas valen más que coincidencias parciales.
    """
    score = 0.0
    words_in_text = set(re.findall(r'\b\w+\b', text_normalized))

    for kw in keywords:
        kw_norm = _normalize(kw)
        kw_words = set(kw_norm.split())

        # Coincidencia exacta de frase (mayor peso)
        if kw_norm in text_normalized:
            score += 2.0 if len(kw_words) > 1 else 1.5

        # Coincidencia de palabras individuales de la keyword
        elif kw_words & words_in_text:
            overlap = len(kw_words & words_in_text) / len(kw_words)
            score += overlap * 0.8

    return score


def _normalize_scores(scores: Dict[str, float]) -> Dict[str, float]:
    """Normaliza scores al rango [0, 1]."""
    total = sum(scores.values())
    if total == 0:
        return {k: 0.0 for k in scores}
    return {k: v / total for k, v in scores.items()}


def _calculate_confidence(scores_normalized: Dict[str, float], winner_id: str) -> float:
    """
    Calcula confianza basada en qué tan dominante es el ganador.
    Alta confianza = el ganador supera al segundo por un margen significativo.
    """
    sorted_scores = sorted(scores_normalized.values(), reverse=True)
    winner_score = sorted_scores[0]

    if winner_score == 0:
        return 0.0

    second_score = sorted_scores[1] if len(sorted_scores) > 1 else 0.0

    # Confianza = cuánto supera el ganador al segundo lugar
    gap = winner_score - second_score
    confidence = min(winner_score + gap, 1.0)

    return round(confidence, 3)


def classify_archetype(user_input: str) -> ClassificationResult:
    """
    Clasifica el input del usuario y retorna el arquetipo más afín.

    Args:
        user_input: El texto del usuario (pregunta/situación)

    Returns:
        ClassificationResult con arquetipo, confianza y scores detallados
    """
    text_norm = _normalize(user_input)

    # Calcular score por keywords para cada arquetipo
    raw_scores: Dict[str, float] = {}
    for arch_id, archetype in ARCHETYPES.items():
        raw_scores[arch_id] = _keyword_score(text_norm, archetype.keywords)

    # Normalizar scores
    normalized = _normalize_scores(raw_scores)

    # Determinar ganador
    winner_id = max(normalized, key=normalized.get)
    winner_score = normalized[winner_id]

    # Si todos los scores son 0 (sin keywords match), usar fallback semántico
    if winner_score == 0:
        return _semantic_fallback(user_input, raw_scores)

    confidence = _calculate_confidence(normalized, winner_id)
    archetype = ARCHETYPES[winner_id]

    return ClassificationResult(
        archetype_id=winner_id,
        archetype=archetype,
        confidence=confidence,
        scores={k: round(v, 4) for k, v in normalized.items()},
        method="keyword"
    )


def _semantic_fallback(user_input: str, raw_scores: dict) -> ClassificationResult:
    """
    Fallback cuando no hay coincidencias de keywords.
    Usa heurísticas semánticas simples basadas en patrones del texto.
    """
    text_lower = user_input.lower()
    fallback_scores = {k: 0.0 for k in ARCHETYPES}

    # Heurísticas simples de fallback
    if any(w in text_lower for w in ["familia", "madre", "padre", "herencia"]):
        fallback_scores["LA_RAIZ_SAGRADA"] += 1.0
    if any(w in text_lower for w in ["decidir", "elección", "camino", "qué hago"]):
        fallback_scores["EL_UMBRAL"] += 1.0
    if any(w in text_lower for w in ["relación", "pareja", "vínculo", "amor"]):
        fallback_scores["EL_ESPEJO"] += 1.0
    if any(w in text_lower for w in ["trabajo", "profesión", "carrera", "dinero"]):
        fallback_scores["LA_LLAMA"] += 0.8
    if any(w in text_lower for w in ["miedo", "ansiedad", "angustia", "nervios"]):
        fallback_scores["LA_GUARDIANA"] += 1.0

    # Si todavía empate, EL_UMBRAL como default (el más universal)
    if max(fallback_scores.values()) == 0:
        fallback_scores["EL_UMBRAL"] = 1.0

    winner_id = max(fallback_scores, key=fallback_scores.get)
    total = sum(fallback_scores.values())
    normalized = {k: v / total for k, v in fallback_scores.items()} if total > 0 else fallback_scores

    return ClassificationResult(
        archetype_id=winner_id,
        archetype=ARCHETYPES[winner_id],
        confidence=0.5,  # Confianza media en fallback semántico
        scores={k: round(v, 4) for k, v in normalized.items()},
        method="semantic_fallback"
    )


def get_top_archetypes(user_input: str, n: int = 3) -> List[ClassificationResult]:
    """
    Retorna los N arquetipos más afines al input (útil para debug y análisis).
    """
    text_norm = _normalize(user_input)
    raw_scores: Dict[str, float] = {
        arch_id: _keyword_score(text_norm, archetype.keywords)
        for arch_id, archetype in ARCHETYPES.items()
    }
    normalized = _normalize_scores(raw_scores)
    sorted_ids = sorted(normalized, key=normalized.get, reverse=True)[:n]

    results = []
    for arch_id in sorted_ids:
        results.append(ClassificationResult(
            archetype_id=arch_id,
            archetype=ARCHETYPES[arch_id],
            confidence=normalized[arch_id],
            scores=normalized,
            method="keyword"
        ))
    return results
