"""Capa de acceso al modelo Gemini: creación de cliente y llamada de edición."""

from google import genai
from google.genai import types

from config import MODEL_NAME, SYSTEM_INSTRUCTION


def get_client(api_key: str) -> genai.Client:
    """Crea un cliente de Gemini a partir de la API key del usuario."""
    return genai.Client(api_key=api_key)


def mejorar_texto(client: genai.Client, texto: str, temperatura: float) -> str:
    """Envía el texto al modelo y devuelve la versión editada.

    Lanza las excepciones tal como las emite el SDK (google.genai.errors)
    para que la capa de UI decida cómo mostrarlas.
    """
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=texto,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=temperatura,
        ),
    )
    if not response.text:
        raise ValueError(
            "El modelo no devolvió texto. Es posible que el contenido haya "
            "sido bloqueado por los filtros de seguridad de Gemini."
        )
    return response.text
