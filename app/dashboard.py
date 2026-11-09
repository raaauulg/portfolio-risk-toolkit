"""Punto de entrada del dashboard: streamlit run app/dashboard.py

Pinta la barra lateral, calcula (con caché) la configuración aplicada y delega en
la página elegida. Todas las cifras proceden del toolkit miax_toolkit.
"""

import sys
from pathlib import Path

# «streamlit run» solo añade app/ a sys.path; se añade la raíz para importar el paquete app.
RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import streamlit as st  # noqa: E402

from app import barra_lateral, componentes, datos, estilo  # noqa: E402
from app.configuracion import MAX_ACTIVOS, PRESETS  # noqa: E402

st.set_page_config(page_title="MIAX · Analizador de carteras", page_icon=":material/monitoring:",
                   layout="wide", initial_sidebar_state="expanded")
st.markdown(estilo.CSS, unsafe_allow_html=True)

barra_lateral.inicializar()
# ?preset=demo en la URL deja la demo cargada al abrir (capturas y marcador de la presentación).
preset_url = st.query_params.get("preset")
if preset_url in PRESETS and not st.session_state.get("preset_url_aplicado"):
    st.session_state["preset_url_aplicado"] = True
    barra_lateral.aplicar_preset(preset_url)
barra_lateral.dibujar()

config = st.session_state.get("config_aplicada")
st.session_state["resultados"] = None
if config is not None:
    try:
        if len(config.activos) > MAX_ACTIVOS:
            raise ValueError(f"El dashboard admite como máximo {MAX_ACTIVOS} activos (uno por color de la paleta).")
        with st.spinner("Calculando: datos, cartera, Monte Carlo e informe…"):
            st.session_state["resultados"] = datos.resultados(config)
    except Exception as error:  # nunca un traceback en pantalla
        componentes.mostrar_error(error, config.modo)

paginas = [
    st.Page("paginas/resumen.py", title="Resumen", icon=":material/dashboard:", default=True),
    st.Page("paginas/datos_calidad.py", title="Datos y calidad", icon=":material/fact_check:", url_path="datos"),
    st.Page("paginas/cartera_riesgo.py", title="Cartera y riesgo", icon=":material/pie_chart:", url_path="riesgo"),
    st.Page("paginas/monte_carlo.py", title="Monte Carlo", icon=":material/stacked_line_chart:", url_path="monte_carlo"),
    st.Page("paginas/informe.py", title="Informe", icon=":material/description:", url_path="informe"),
    st.Page("paginas/arquitectura.py", title="Arquitectura", icon=":material/account_tree:", url_path="arquitectura"),
]
st.navigation(paginas, position="top").run()
