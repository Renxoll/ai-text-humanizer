"""Componentes de interfaz reutilizables: copiar al portapapeles y vista de pantalla completa."""

import html
import json

import streamlit as st
import streamlit.components.v1 as components


def boton_copiar(texto: str, key: str, etiqueta: str = "📋 Copiar") -> None:
    """Renderiza un botón que copia `texto` al portapapeles del navegador del usuario."""
    texto_js = json.dumps(texto)
    componente_html = f"""
    <div style="margin-top:4px;">
        <button id="btn-{key}" style="
            background-color:#2563eb;color:white;border:none;border-radius:6px;
            padding:6px 14px;font-size:0.85rem;cursor:pointer;">
            {etiqueta}
        </button>
        <span id="msg-{key}" style="margin-left:8px;font-size:0.8rem;color:#16a34a;"></span>
    </div>
    <script>
        const btn_{key} = document.getElementById("btn-{key}");
        btn_{key}.addEventListener("click", async () => {{
            try {{
                await navigator.clipboard.writeText({texto_js});
                document.getElementById("msg-{key}").innerText = "¡Copiado!";
                setTimeout(() => {{ document.getElementById("msg-{key}").innerText = ""; }}, 2000);
            }} catch (err) {{
                document.getElementById("msg-{key}").innerText = "No se pudo copiar";
            }}
        }});
    </script>
    """
    components.html(componente_html, height=40)


@st.dialog("Texto completo", width="large")
def _dialogo_pantalla_completa() -> None:
    texto = st.session_state.get("_texto_dialogo", "")
    st.markdown(
        f'<div style="font-size:1.05rem;line-height:1.8;white-space:pre-wrap;">{html.escape(texto)}</div>',
        unsafe_allow_html=True,
    )
    st.divider()
    boton_copiar(texto, key="dialogo")


def mostrar_pantalla_completa(texto: str) -> None:
    """Abre un modal grande mostrando `texto` completo, con su propio botón de copiar."""
    st.session_state["_texto_dialogo"] = texto
    _dialogo_pantalla_completa()
