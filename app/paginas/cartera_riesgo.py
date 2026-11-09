"""Página 3 · Cartera y riesgo: composición, aportación al riesgo, correlaciones, caídas y volatilidad."""

import pandas as pd
import streamlit as st

from app import componentes, graficos, transformaciones
from app.formato import numero, porcentaje

VENTANAS = {21: "21 · 1 mes", 63: "63 · 3 meses", 126: "126 · 6 meses"}

res =componentes.resultados_o_estado_vacio()
modo = componentes.modo_tema()
componentes.cabecera("Cartera y riesgo", res)
opciones = {"displaylogo": False}
pesos = pd.Series(res.cartera.obtener_pesos())

col1, col2 = st.columns(2)
col1.plotly_chart(graficos.composicion(pesos, modo), width="stretch", config=opciones)
col2.plotly_chart(graficos.peso_vs_riesgo(pesos, res.riesgo, modo), width="stretch", config=opciones)
st.caption("Aportación al riesgo de reportes.contribucion_riesgo(): aproximación con los pesos iniciales "
           "fijos; en comprar y mantener los pesos efectivos cambian con los precios.")

st.subheader("Métricas por activo")
tabla = pd.DataFrame([{
    "Activo": a, "Peso": porcentaje(pesos[a]), "Aportación al riesgo": porcentaje(res.riesgo[a]),
    "Rentabilidad anual": porcentaje(m["rent_anual"]), "Volatilidad anual": porcentaje(m["volatilidad"]),
    "Sharpe": numero(m["sharpe"]), "Caída máxima": porcentaje(m["caida_maxima"]),
} for a, m in res.metricas_activos.items()])
st.dataframe(tabla, hide_index=True, width="stretch")

st.plotly_chart(graficos.correlacion(res.correlacion, modo), width="stretch", config=opciones)

st.subheader("Caídas y volatilidad")
st.caption("Caídas, volatilidad móvil y rendimientos diarios se derivan del valor de la cartera con "
           "las mismas fórmulas que las figuras del toolkit. VaR y CVaR son los de reportes.metricas().")
ventana = st.segmented_control("Ventana de la volatilidad móvil (sesiones)", list(VENTANAS), default=63,
                               format_func=VENTANAS.get, key="ventana_volatilidad") or 63
col1, col2 = st.columns(2)
col1.plotly_chart(graficos.caidas(transformaciones.caidas(res.valores), res.config.nombre, modo),
                  width="stretch", config=opciones)
col2.plotly_chart(graficos.volatilidad_movil(transformaciones.volatilidad_movil(res.valores, ventana),
                                             ventana, modo), width="stretch", config=opciones)
st.plotly_chart(graficos.distribucion_rendimientos(
    transformaciones.rendimientos(res.valores), res.metricas["var"], res.metricas["cvar"],
    res.config.nivel_var, modo), width="stretch", config=opciones)
componentes.glosario()
