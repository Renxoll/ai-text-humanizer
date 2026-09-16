"""Capa de acceso al modelo Gemini: creación de cliente y llamada de edición."""

from google import genai
from google.genai import types
from google.genai import errors as genai_errors

from config import FALLBACK_MODELS, MODEL_NAME, SYSTEM_INSTRUCTION


def get_client(api_key: str) -> genai.Client:
    """Crea un cliente de Gemini a partir de la API key del usuario."""
    return genai.Client(api_key=api_key)


def _generar_con_modelo(client: genai.Client, modelo: str, texto: str, temperatura: float) -> str:
    """Llama a un modelo puntual y valida que haya devuelto texto."""
    response = client.models.generate_content(
        model=modelo,
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


def mejorar_texto(client: genai.Client, texto: str, temperatura: float) -> tuple[str, str]:
    """Envía el texto al modelo principal y devuelve la versión editada.

    Si el modelo principal responde 503 (saturado por alta demanda), reintenta
    en orden con los modelos de FALLBACK_MODELS hasta que alguno responda.
    Cualquier otra excepción (clave inválida, cuota, bloqueo de contenido) se
    propaga de inmediato, sin probar alternativas.

    Devuelve una tupla (texto_editado, nombre_del_modelo_que_respondió), para
    que la capa de UI pueda informar si se usó un modelo alternativo.
    """
    candidatos = [MODEL_NAME] + FALLBACK_MODELS
    ultimo_error: genai_errors.ServerError | None = None

    for modelo in candidatos:
        try:
            resultado = _generar_con_modelo(client, modelo, texto, temperatura)
            return resultado, modelo
        except genai_errors.ServerError as e:
            if e.code == 503:
                ultimo_error = e
                continue
            raise

    assert ultimo_error is not None
    raise ultimo_error
