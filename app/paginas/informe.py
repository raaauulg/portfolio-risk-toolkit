"""Página 5 · Informe: report() en Markdown y las figuras de plots_report(), tal como las genera el toolkit."""

import streamlit as st

from miax_toolkit.reportes import SECCIONES

from app import componentes, datos

NOMBRES_SECCION = {"resumen": "Métricas", "composicion": "Composición", "activos": "Métricas por activo",
                   "correlaciones": "Correlaciones", "montecarlo": "Monte Carlo",
                   "diagnostico": "Diagnóstico", "advertencias": "Advertencias"}
NOMBRES_FIGURA = {"rendimiento": "Rendimiento", "correlacion": "Correlación", "evolucion": "Evolución",
                  "riesgo": "Riesgo", "montecarlo": "Monte Carlo"}

res = componentes.resultados_o_estado_vacio()
componentes.cabecera("Informe", res)
st.caption("Salida literal del núcleo: Cartera.report() y Cartera.plots_report(). Tasa libre y nivel de VaR "
           "se cambian en el paso 3 de la barra lateral.")

secciones = st.pills("Secciones del informe", SECCIONES, selection_mode="multi", default=list(SECCIONES),
                     format_func=NOMBRES_SECCION.get, key="secciones_informe")
if not secciones:
    st.info("Elige al menos una sección.", icon=":material/info:")
else:
    texto = res.cartera.report(
        secciones=tuple(s for s in SECCIONES if s in secciones), tasa_libre=res.config.tasa_libre,
        nivel_var=res.config.nivel_var, simulacion=res.simulacion,
        benchmark=None if res.benchmark is None else res.benchmark.precios)
    st.download_button("Descargar informe (.md)", texto.encode("utf-8"), file_name="informe.md",
                       mime="text/markdown", icon=":material/download:")
    with st.container(border=True):
        st.markdown(texto)

st.subheader("Figuras del toolkit")
with st.spinner("Generando las figuras de matplotlib…"):
    imagenes = datos.figuras_toolkit_png(res.config)
pestanas = st.tabs([NOMBRES_FIGURA[n] for n in imagenes])
for pestana, (nombre, png) in zip(pestanas, imagenes.items()):
    with pestana:
        figura, _ = st.columns([5, 1])  # ancho contenido: la figura no se desborda a 1366 px
        figura.image(png, width="stretch",
                     caption=f"{NOMBRES_FIGURA[nombre]} · figura de matplotlib del toolkit")
        st.download_button("Descargar PNG", png, file_name=f"{nombre}.png", mime="image/png",
                           key=f"png_{nombre}", icon=":material/download:")
