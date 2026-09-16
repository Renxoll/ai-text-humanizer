"""
Asistente de Edición y Estilo Académico
----------------------------------------
Aplicación Streamlit que ayuda a mejorar la redacción de textos académicos
ya escritos por el propio usuario: detecta palabras y estructuras
repetitivas, sugiere alternativas léxicas más precisas que la primera
opción "obvia", y varía la longitud/forma de las oraciones para lograr
una lectura más natural y fluida, preservando siempre el significado,
los datos y los hechos originales.

Incluye una vista de pantalla completa, un botón de copiado rápido y un
chat de ajustes para pedir correcciones puntuales con interacción humana
sobre la edición ya generada.

Requiere una API Key de Gemini propia del usuario (no se almacena ni se
envía a ningún servidor distinto de la API oficial de Google).

Este archivo contiene solo la capa de interfaz; la lógica de negocio vive
en config.py, gemini_service.py, diff_utils.py y ui_helpers.py para
facilitar su reuso (por ejemplo, en una futura CLI o API).
"""

import streamlit as st
from google.genai import errors as genai_errors

from config import (
    CHAT_UPDATE_END,
    CHAT_UPDATE_START,
    DEFAULT_TEMPERATURE,
    FALLBACK_MODELS,
    MODEL_NAME,
    PAGE_CONFIG,
    TEMPERATURE_MAX,
    TEMPERATURE_MIN,
    TEMPERATURE_STEP,
)
from diff_utils import generar_diff_html
from gemini_service import crear_chat, enviar_mensaje_chat, get_client, mejorar_texto
from ui_helpers import boton_copiar, mostrar_pantalla_completa

st.set_page_config(**PAGE_CONFIG)

if "resultado" not in st.session_state:
    st.session_state.resultado = ""
if "texto_procesado" not in st.session_state:
    st.session_state.texto_procesado = ""
if "modelo_usado" not in st.session_state:
    st.session_state.modelo_usado = ""
if "chat" not in st.session_state:
    st.session_state.chat = None
if "chat_mensajes" not in st.session_state:
    st.session_state.chat_mensajes = []


def mostrar_error_genai(e: Exception) -> None:
    """Muestra un mensaje de error legible según el tipo de excepción del SDK."""
    if isinstance(e, genai_errors.ClientError):
        if e.code in (401, 403):
            st.error(
                "🔑 La API Key ingresada no es válida o no tiene permisos. "
                "Verifica tu clave en Google AI Studio."
            )
        elif e.code == 429:
            st.error(
                "⏳ Se alcanzó el límite de cuota de la API. "
                "Espera unos minutos o revisa tu plan de uso en Google AI Studio."
            )
        else:
            st.error(f"❌ Error del cliente al llamar a la API de Gemini: {e}")
    elif isinstance(e, genai_errors.ServerError):
        st.error(
            "❌ El modelo principal y todos los modelos alternativos están "
            "saturados por alta demanda en este momento. Intenta nuevamente "
            f"en unos minutos. Detalle: {e}"
        )
    elif isinstance(e, ValueError):
        st.warning(str(e))
    else:
        st.error(f"❌ Ocurrió un error inesperado: {e}")


# ---------------------------------------------------------------------------
# Barra lateral: configuración y credenciales
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Configuración")

    api_key = st.text_input(
        "Gemini API Key",
        type="password",
        help="Tu clave personal de Google AI Studio. No se almacena ni se comparte.",
    )

    temperatura = st.slider(
        "Variación estilística",
        min_value=TEMPERATURE_MIN,
        max_value=TEMPERATURE_MAX,
        value=DEFAULT_TEMPERATURE,
        step=TEMPERATURE_STEP,
        help=(
            "Valores más altos generan mayor variedad léxica y de "
            "estructura de oraciones; valores más bajos producen ediciones "
            "más conservadoras."
        ),
    )

    st.caption(f"Modelo principal: `{MODEL_NAME}`")
    with st.expander("Modelos de respaldo (si hay saturación)"):
        st.caption(
            "Si el modelo principal responde con error 503 (alta demanda), "
            "se reintenta automáticamente en este orden:"
        )
        for m in FALLBACK_MODELS:
            st.caption(f"• `{m}`")
    st.divider()
    st.caption(
        "Esta herramienta edita y mejora la redacción de textos que ya "
        "escribiste. Preserva el significado, los datos y las fuentes "
        "originales; no genera contenido nuevo."
    )


# ---------------------------------------------------------------------------
# Cuerpo principal
# ---------------------------------------------------------------------------
st.title("📝 Asistente de Edición y Estilo Académico")
st.write(
    "Pega tu borrador y la aplicación identificará palabras y estructuras "
    "repetitivas, sugiriendo alternativas más precisas y variadas, sin "
    "cambiar el significado, los datos ni las fuentes del texto original."
)

col_input, col_output = st.columns(2)

with col_input:
    st.subheader("Texto original")
    texto_original = st.text_area(
        "Ingresa tu texto académico",
        height=400,
        placeholder="Pega aquí tu borrador...",
        label_visibility="collapsed",
    )
    procesar = st.button("✨ Mejorar redacción", type="primary", use_container_width=True)

with col_output:
    st.subheader("Texto editado")
    tab_resultado, tab_diff, tab_chat = st.tabs(
        ["Resultado", "🔍 Comparar cambios", "💬 Pedir ajustes"]
    )

    with tab_resultado:
        st.text_area(
            "Resultado",
            value=st.session_state.resultado,
            height=380,
            placeholder="Aquí aparecerá el texto mejorado...",
            label_visibility="collapsed",
            disabled=True,
        )
        if st.session_state.resultado:
            col_a, col_b = st.columns([1, 1])
            with col_a:
                if st.button("🔎 Ver en pantalla completa", use_container_width=True):
                    mostrar_pantalla_completa(st.session_state.resultado)
            with col_b:
                boton_copiar(st.session_state.resultado, key="resultado_principal")

    with tab_diff:
        if st.session_state.resultado:
            diff_html = generar_diff_html(st.session_state.texto_procesado, st.session_state.resultado)
            st.markdown(diff_html, unsafe_allow_html=True)
            st.caption("🔴 Tachado = texto eliminado del original · 🟢 Resaltado = texto agregado/modificado")
        else:
            st.info("Genera una edición para ver aquí la comparación palabra por palabra.")

    with tab_chat:
        if not st.session_state.resultado:
            st.info("Genera una edición primero para poder pedir ajustes o sugerencias sobre ella.")
        else:
            st.caption(
                "Pregunta por qué se hizo un cambio, pide otra sugerencia, o solicita un "
                "ajuste puntual (p. ej. \"usa un sinónimo menos formal para 'sin embargo'\")."
            )
            for msg in st.session_state.chat_mensajes:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            mensaje_usuario = st.chat_input("Escribe tu pregunta o el ajuste que quieres pedir...")
            if mensaje_usuario:
                if not api_key.strip():
                    st.error("⚠️ Ingresa tu Gemini API Key en la barra lateral antes de continuar.")
                else:
                    st.session_state.chat_mensajes.append({"role": "user", "content": mensaje_usuario})
                    try:
                        if st.session_state.chat is None:
                            client = get_client(api_key)
                            st.session_state.chat = crear_chat(
                                client,
                                st.session_state.texto_procesado,
                                st.session_state.resultado,
                                temperatura,
                            )

                        with st.spinner("Pensando una respuesta..."):
                            respuesta = enviar_mensaje_chat(st.session_state.chat, mensaje_usuario)

                        if CHAT_UPDATE_START in respuesta and CHAT_UPDATE_END in respuesta:
                            explicacion, resto = respuesta.split(CHAT_UPDATE_START, 1)
                            texto_actualizado, _ = resto.split(CHAT_UPDATE_END, 1)
                            texto_actualizado = texto_actualizado.strip()

                            st.session_state.resultado = texto_actualizado
                            mensaje_mostrado = (
                                explicacion.strip()
                                or "Listo, actualicé el texto según tu pedido."
                            ) + "\n\n✅ *Se actualizó el resultado en la pestaña **Resultado**.*"
                        else:
                            mensaje_mostrado = respuesta.strip()

                        st.session_state.chat_mensajes.append(
                            {"role": "assistant", "content": mensaje_mostrado}
                        )
                        st.rerun()

                    except Exception as e:
                        st.session_state.chat_mensajes.pop()  # descarta el mensaje del usuario que falló
                        mostrar_error_genai(e)


# ---------------------------------------------------------------------------
# Lógica de procesamiento y manejo de errores
# ---------------------------------------------------------------------------
if procesar:
    if not api_key.strip():
        st.error("⚠️ Ingresa tu Gemini API Key en la barra lateral antes de continuar.")
    elif not texto_original.strip():
        st.warning("⚠️ El campo de texto está vacío. Ingresa un texto para editar.")
    else:
        try:
            with st.spinner("Analizando patrones repetitivos y mejorando la redacción..."):
                client = get_client(api_key)
                resultado, modelo_usado = mejorar_texto(client, texto_original, temperatura)

            st.session_state.resultado = resultado
            st.session_state.texto_procesado = texto_original
            st.session_state.modelo_usado = modelo_usado
            # Una nueva edición invalida la conversación de ajustes anterior.
            st.session_state.chat = None
            st.session_state.chat_mensajes = []

            if modelo_usado == MODEL_NAME:
                st.success("✅ Texto editado con éxito. Revisa la pestaña 'Comparar cambios' para ver el detalle.")
            else:
                st.success(
                    f"✅ Texto editado con éxito usando el modelo alternativo `{modelo_usado}` "
                    f"(`{MODEL_NAME}` estaba saturado por alta demanda). "
                    "Revisa la pestaña 'Comparar cambios' para ver el detalle."
                )
            st.rerun()

        except Exception as e:
            mostrar_error_genai(e)
