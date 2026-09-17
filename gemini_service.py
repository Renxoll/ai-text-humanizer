"""Capa de acceso al modelo Gemini: creación de cliente y llamada de edición."""

from google import genai
from google.genai import types
from google.genai import errors as genai_errors

from google.genai.chats import Chat

from config import CHAT_SYSTEM_INSTRUCTION, FALLBACK_MODELS, MODEL_NAME, SYSTEM_INSTRUCTION


def get_client(api_key: str) -> genai.Client:
    """Crea un cliente de Gemini a partir de la API key del usuario."""
    return genai.Client(api_key=api_key)


def _con_instrucciones_estilo(instruccion_base: str, instrucciones_estilo: str) -> str:
    """Añade al final de una instrucción base las preferencias de estilo del usuario, si las hay."""
    if not instrucciones_estilo.strip():
        return instruccion_base
    return (
        f"{instruccion_base}\n\n"
        "Instrucción adicional de estilo indicada por el usuario para esta "
        "tarea (respétala siempre que no contradiga las reglas anteriores, "
        "en especial la de no alterar significado, datos ni citas):\n"
        f"{instrucciones_estilo.strip()}"
    )


def _generar_con_modelo(
    client: genai.Client,
    modelo: str,
    texto: str,
    temperatura: float,
    instrucciones_estilo: str = "",
) -> str:
    """Llama a un modelo puntual y valida que haya devuelto texto."""
    response = client.models.generate_content(
        model=modelo,
        contents=texto,
        config=types.GenerateContentConfig(
            system_instruction=_con_instrucciones_estilo(SYSTEM_INSTRUCTION, instrucciones_estilo),
            temperature=temperatura,
        ),
    )
    if not response.text:
        raise ValueError(
            "El modelo no devolvió texto. Es posible que el contenido haya "
            "sido bloqueado por los filtros de seguridad de Gemini."
        )
    return response.text


def mejorar_texto(
    client: genai.Client,
    texto: str,
    temperatura: float,
    instrucciones_estilo: str = "",
) -> tuple[str, str]:
    """Envía el texto al modelo principal y devuelve la versión editada.

    Si el modelo principal responde 503 (saturado por alta demanda), reintenta
    en orden con los modelos de FALLBACK_MODELS hasta que alguno responda.
    Cualquier otra excepción (clave inválida, cuota, bloqueo de contenido) se
    propaga de inmediato, sin probar alternativas.

    `instrucciones_estilo` son preferencias libres del usuario (p. ej. "tono
    más conversacional", "dirigido a un público no experto") que se añaden a
    las reglas base del editor para esta ejecución.

    Devuelve una tupla (texto_editado, nombre_del_modelo_que_respondió), para
    que la capa de UI pueda informar si se usó un modelo alternativo.
    """
    candidatos = [MODEL_NAME] + FALLBACK_MODELS
    ultimo_error: genai_errors.ServerError | None = None

    for modelo in candidatos:
        try:
            resultado = _generar_con_modelo(client, modelo, texto, temperatura, instrucciones_estilo)
            return resultado, modelo
        except genai_errors.ServerError as e:
            if e.code == 503:
                ultimo_error = e
                continue
            raise

    assert ultimo_error is not None
    raise ultimo_error


def crear_chat(
    client: genai.Client,
    texto_original: str,
    texto_editado: str,
    temperatura: float,
    instrucciones_estilo: str = "",
) -> Chat:
    """Crea una sesión de chat multi-turno para pedir ajustes sobre la edición.

    Se siembra con el texto original y la primera versión editada como
    contexto, para que el usuario pueda pedir correcciones o hacer preguntas
    de seguimiento sin repetir el texto en cada mensaje.
    """
    return client.chats.create(
        model=MODEL_NAME,
        config=types.GenerateContentConfig(
            system_instruction=_con_instrucciones_estilo(CHAT_SYSTEM_INSTRUCTION, instrucciones_estilo),
            temperature=temperatura,
        ),
        history=[
            types.Content(role="user", parts=[types.Part(text=f"Texto original:\n\n{texto_original}")]),
            types.Content(role="model", parts=[types.Part(text=texto_editado)]),
        ],
    )


def enviar_mensaje_chat(chat: Chat, mensaje: str) -> str:
    """Envía un mensaje de seguimiento en la sesión de chat y devuelve la respuesta."""
    response = chat.send_message(mensaje)
    if not response.text:
        raise ValueError(
            "El modelo no devolvió texto. Es posible que el contenido haya "
            "sido bloqueado por los filtros de seguridad de Gemini."
        )
    return response.text
