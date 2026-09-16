"""
Asistente de Edición y Estilo Académico
----------------------------------------
Aplicación Streamlit que ayuda a mejorar la redacción de textos académicos
ya escritos por el propio usuario: detecta palabras y estructuras
repetitivas, sugiere alternativas léxicas más precisas que la primera
opción "obvia", y varía la longitud/forma de las oraciones para lograr
una lectura más natural y fluida, preservando siempre el significado,
los datos y los hechos originales.

Requiere una API Key de Gemini propia del usuario (no se almacena ni se
envía a ningún servidor distinto de la API oficial de Google).

Este archivo contiene solo la capa de interfaz; la lógica de negocio vive
en config.py, gemini_service.py y diff_utils.py para facilitar su reuso
(por ejemplo, en una futura CLI o API).
"""

import streamlit as st
from google.genai import errors as genai_errors

from config import (
    DEFAULT_TEMPERATURE,
    FALLBACK_MODELS,
    MODEL_NAME,
    PAGE_CONFIG,
    TEMPERATURE_MAX,
    TEMPERATURE_MIN,
    TEMPERATURE_STEP,
)
from diff_utils import generar_diff_html
from gemini_service import get_client, mejorar_texto

st.set_page_config(**PAGE_CONFIG)

if "resultado" not in st.session_state:
    st.session_state.resultado = ""
if "texto_procesado" not in st.session_state:
    st.session_state.texto_procesado = ""
if "modelo_usado" not in st.session_state:
    st.session_state.modelo_usado = ""


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
    tab_resultado, tab_diff = st.tabs(["Resultado", "🔍 Comparar cambios"])

    with tab_resultado:
        resultado_placeholder = st.empty()
        resultado_placeholder.text_area(
            "Resultado",
            value=st.session_state.resultado,
            height=380,
            placeholder="Aquí aparecerá el texto mejorado...",
            label_visibility="collapsed",
            disabled=True,
        )

    with tab_diff:
        diff_placeholder = st.empty()
        if st.session_state.resultado:
            diff_html = generar_diff_html(st.session_state.texto_procesado, st.session_state.resultado)
            diff_placeholder.markdown(diff_html, unsafe_allow_html=True)
            st.caption("🔴 Tachado = texto eliminado del original · 🟢 Resaltado = texto agregado/modificado")
        else:
            diff_placeholder.info("Genera una edición para ver aquí la comparación palabra por palabra.")


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

            if modelo_usado == MODEL_NAME:
                st.success("✅ Texto editado con éxito. Revisa la pestaña 'Comparar cambios' para ver el detalle.")
            else:
                st.success(
                    f"✅ Texto editado con éxito usando el modelo alternativo `{modelo_usado}` "
                    f"(`{MODEL_NAME}` estaba saturado por alta demanda). "
                    "Revisa la pestaña 'Comparar cambios' para ver el detalle."
                )
            st.rerun()

        except genai_errors.ClientError as e:
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

        except genai_errors.ServerError as e:
            st.error(
                "❌ El modelo principal y todos los modelos alternativos están "
                "saturados por alta demanda en este momento. Intenta nuevamente "
                f"en unos minutos. Detalle: {e}"
            )

        except ValueError as e:
            st.warning(str(e))

        except Exception as e:
            st.error(f"❌ Ocurrió un error inesperado: {e}")
