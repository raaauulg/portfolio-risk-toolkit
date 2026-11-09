"""Página 2 · Datos y calidad: contrato de datos, diagnóstico de limpieza y descargas."""

import pandas as pd
import streamlit as st

from miax_toolkit.reportes import valor_cartera

from app import componentes, graficos
from app.formato import fecha, numero

res = componentes.resultados_o_estado_vacio()
modo = componentes.modo_tema()
componentes.cabecera("Datos y calidad", res)

st.subheader("Contrato de datos por serie")
series = [*(res.series[a] for a in res.config.activos), *([res.benchmark] if res.benchmark else [])]
contrato = pd.DataFrame([{
    "Ticker": s.ticker, "Fuente": s.fuente, "Tipo": s.tipo_activo, "Moneda": s.moneda,
    "Frecuencia": s.frecuencia, "Ajuste": s.ajuste.replace("_", " "), "Unidad": s.unidad,
    "Observaciones": len(s.precios), "Desde": fecha(s.precios.index[0]), "Hasta": fecha(s.precios.index[-1]),
    "Media del precio": numero(s.media), "Desv. típica del precio": numero(s.desviacion_tipica),
} for s in series])
st.dataframe(contrato, hide_index=True, width="stretch")
st.caption("Media y desviación típica las calcula SeriePrecios al crearse y son de **niveles de precio**, "
           "no de rentabilidades: dependen del periodo y dicen poco del riesgo. El riesgo está en "
           "«Cartera y riesgo».")

st.subheader("Diagnóstico de limpieza y alineación")
st.caption("Resumen que devuelve alinear_precios() del toolkit: no se rellenan festivos ni huecos.")
for linea in res.diagnostico:
    if linea.startswith("AVISO"):
        st.warning(linea.removeprefix("AVISO "), icon=":material/error:")
    elif linea.startswith("Alineación"):
        st.info(linea, icon=":material/event_busy:")
    else:
        st.markdown(f"- {linea}")
if res.referencia is not None and len(res.tabla_analisis) < len(res.tabla):
    st.info(f"Benchmark: el análisis usa {len(res.tabla_analisis)} de {len(res.tabla)} fechas comunes "
            f"porque {res.nombre_ref} no cotiza en el resto. No se rellenan precios.",
            icon=":material/event_busy:")

# Base 100 de cada activo con la función del toolkit (cartera de un solo activo).
base100 = pd.DataFrame({a: valor_cartera(res.tabla[[a]], {a: 1.0}) for a in res.tabla.columns})
st.plotly_chart(graficos.precios_base100(base100, modo), width="stretch", config={"displaylogo": False})

st.subheader("Descargas")
col1, col2 = st.columns(2)
col1.download_button("Precios alineados (CSV)", res.tabla.to_csv(index_label="fecha").encode("utf-8"),
                     file_name="precios_alineados.csv", mime="text/csv", icon=":material/download:",
                     help="Cierres en las fechas comunes a todos los activos, tal como entran en el análisis.")
originales = pd.concat({s.ticker: s.precios for s in series}, axis=1)
col2.download_button("Precios originales (CSV)", originales.to_csv(index_label="fecha").encode("utf-8"),
                     file_name="precios_originales.csv", mime="text/csv", icon=":material/download:",
                     help="Cada serie con su propio calendario (celdas vacías donde no cotiza).")
componentes.glosario()
