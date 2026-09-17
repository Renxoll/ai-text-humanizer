"""Diagnóstico local de estilo: muletillas y variedad de longitud de oraciones.

No llama a la API de Gemini ni estima "detectabilidad" ante ningún sistema;
es retroalimentación de calidad de escritura, calculada con reglas simples
sobre el propio texto del usuario.
"""

import re
import statistics

from config import CLICHE_PHRASES

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_WORD_RE = re.compile(r"\w+", re.UNICODE)


def detectar_cliches(texto: str) -> dict[str, int]:
    """Cuenta ocurrencias de frases y muletillas genéricas en el texto."""
    texto_lower = texto.lower()
    encontrados = {}
    for frase in CLICHE_PHRASES:
        conteo = texto_lower.count(frase.lower())
        if conteo > 0:
            encontrados[frase] = conteo
    return dict(sorted(encontrados.items(), key=lambda item: item[1], reverse=True))


def _longitudes_oraciones(texto: str) -> list[int]:
    oraciones = [o for o in _SENTENCE_SPLIT_RE.split(texto.strip()) if o.strip()]
    longitudes = [len(_WORD_RE.findall(o)) for o in oraciones]
    return [n for n in longitudes if n > 0]


def analizar_variedad_oraciones(texto: str) -> dict:
    """Estadísticas simples de longitud de oraciones (en palabras).

    Una desviación estándar baja respecto al promedio indica oraciones muy
    uniformes en extensión; valores más altos indican mayor variedad de
    ritmo (mezcla de oraciones cortas y largas).
    """
    longitudes = _longitudes_oraciones(texto)
    if len(longitudes) < 2:
        return {
            "num_oraciones": len(longitudes),
            "promedio": float(longitudes[0]) if longitudes else 0.0,
            "desviacion": 0.0,
            "minimo": longitudes[0] if longitudes else 0,
            "maximo": longitudes[0] if longitudes else 0,
        }
    return {
        "num_oraciones": len(longitudes),
        "promedio": round(statistics.mean(longitudes), 1),
        "desviacion": round(statistics.stdev(longitudes), 1),
        "minimo": min(longitudes),
        "maximo": max(longitudes),
    }
