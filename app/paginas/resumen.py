"""Página 1 · Resumen: KPI frente al benchmark, evolución y advertencias del informe."""

import streamlit as st

from app import componentes, graficos
from app.formato import numero, porcentaje, puntos
from app.textos import GLOSARIO

res = componentes.resultados_o_estado_vacio()
modo = componentes.modo_tema()
componentes.cabecera("Resumen", res)

m, ref = res.metricas, res.metricas_ref
nombre_ref = res.nombre_ref
resumen_mc = res.simulacion.resumen()
nivel = porcentaje(res.config.nivel_var, 0)


def _frente(clave: str) -> str | None:
    """Diferencia frente al benchmark en puntos porcentuales, o None si no hay benchmark."""
    if ref is None:
        return None
    return f"{puntos(m[clave] - ref[clave])} vs {nombre_ref}"


delta_sharpe = None
if ref is not None:
    diferencia = m["sharpe"] - ref["sharpe"]
    delta_sharpe = f"{'+' if diferencia > 0 else ''}{numero(diferencia)} vs {nombre_ref}"

fila1 = st.columns(3)
componentes.tarjeta(fila1[0], "Rentabilidad anualizada", porcentaje(m["rent_anual"]),
                    GLOSARIO["Rentabilidad anualizada"], _frente("rent_anual"), "normal")
componentes.tarjeta(fila1[1], "Volatilidad anualizada", porcentaje(m["volatilidad"]),
                    GLOSARIO["Volatilidad anualizada"], _frente("volatilidad"), "inverse")
componentes.tarjeta(fila1[2], f"Ratio de Sharpe (tasa libre {porcentaje(res.config.tasa_libre, 2)})",
                    numero(m["sharpe"]), GLOSARIO["Ratio de Sharpe"], delta_sharpe, "normal")
fila2 = st.columns(3)
componentes.tarjeta(fila2[0], "Caída máxima", porcentaje(m["caida_maxima"]),
                    GLOSARIO["Caída máxima (drawdown)"], _frente("caida_maxima"), "normal")
componentes.tarjeta(fila2[1], f"VaR diario al {nivel}", porcentaje(m["var"]),
                    GLOSARIO["VaR histórico"] + " " + GLOSARIO["CVaR histórico"],
                    f"CVaR: {porcentaje(m['cvar'])}", flecha=False)
componentes.tarjeta(
    fila2[2], "Probabilidad de pérdida simulada", porcentaje(resumen_mc["prob_perdida"]),
    "Porcentaje de escenarios de Monte Carlo que terminan por debajo del valor inicial.",
    f"a {res.config.horizonte} días de mercado · nu = {res.config.nu:g}", flecha=False)
if ref is not None:
    st.caption(f"Flechas: diferencia frente a {nombre_ref} en las mismas fechas. En volatilidad, una flecha "
               "hacia abajo es favorable. Métricas históricas: no garantizan resultados futuros.")

st.plotly_chart(graficos.evolucion(res.valores, res.valores_ref, res.config.nombre, nombre_ref, modo),
                width="stretch", config={"displaylogo": False})

st.subheader("Advertencias de riesgo")
st.caption("Generadas por el informe del toolkit a partir de los datos (umbrales configurables en report()).")
componentes.advertencias(res.advertencias, res.informe)
componentes.glosario()
