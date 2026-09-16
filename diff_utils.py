"""Utilidades para comparar visualmente el texto original y el editado."""

import difflib
import html
import re

_TOKEN_RE = re.compile(r"\s+|\w+|[^\w\s]", re.UNICODE)

_DEL_STYLE = (
    "background-color:#ffdcdc;color:#8a1f1f;text-decoration:line-through;"
    "border-radius:3px;padding:0 2px;"
)
_INS_STYLE = (
    "background-color:#d7f7d7;color:#1f6b2b;text-decoration:none;"
    "border-radius:3px;padding:0 2px;"
)


def _tokenize(texto: str) -> list[str]:
    """Divide el texto en palabras, puntuación y espacios, preservando todo."""
    return _TOKEN_RE.findall(texto)


def generar_diff_html(original: str, editado: str) -> str:
    """Genera un HTML con las diferencias resaltadas entre dos textos.

    - Texto eliminado del original: tachado en rojo.
    - Texto agregado en la versión editada: resaltado en verde.
    - Texto sin cambios: se muestra tal cual.
    """
    tokens_original = _tokenize(original)
    tokens_editado = _tokenize(editado)

    matcher = difflib.SequenceMatcher(None, tokens_original, tokens_editado, autojunk=False)
    partes: list[str] = []

    for opcode, i1, i2, j1, j2 in matcher.get_opcodes():
        if opcode == "equal":
            partes.append(html.escape("".join(tokens_original[i1:i2])))
        else:
            if i1 != i2:
                texto_borrado = html.escape("".join(tokens_original[i1:i2]))
                partes.append(f'<span style="{_DEL_STYLE}">{texto_borrado}</span>')
            if j1 != j2:
                texto_nuevo = html.escape("".join(tokens_editado[j1:j2]))
                partes.append(f'<span style="{_INS_STYLE}">{texto_nuevo}</span>')

    contenido = "".join(partes)
    return f'<div style="white-space:pre-wrap;line-height:1.6;">{contenido}</div>'
