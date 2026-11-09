"""Página 4 · Monte Carlo: abanico, valor final, interpretación y comparador de colas."""

import pandas as pd
import streamlit as st

from app import componentes, graficos
from app.configuracion import NU_CASI_NORMAL
from app.formato import dinero, numero, porcentaje
from app.textos import AVISO_MONTE_CARLO, GLOSARIO

N_MUESTRA = 30

res = componentes.resultados_o_estado_vacio()
modo = componentes.modo_tema()
componentes.cabecera("Monte Carlo", res)
st.info(AVISO_MONTE_CARLO, icon=":material/info:")

sim, normal = res.simulacion, res.simulacion_normal
r = sim.resumen()
moneda = res.moneda
extremos = sim.percentiles((1, 99)).iloc[-1]  # para recortar el histograma a P1-P99, como el toolkit

fila = st.columns(4)
componentes.tarjeta(fila[0], "Probabilidad de pérdida", porcentaje(r["prob_perdida"]),
                    "Escenarios que terminan por debajo del valor inicial.")
componentes.tarjeta(fila[1], "P5 · desfavorable", dinero(r["P5"], moneda),
                    GLOSARIO["Percentiles (P5, P50, P95)"])
componentes.tarjeta(fila[2], "P50 · mediana", dinero(r["P50"], moneda), GLOSARIO["Percentiles (P5, P50, P95)"])
componentes.tarjeta(fila[3], "P95 · favorable", dinero(r["P95"], moneda),
                    GLOSARIO["Percentiles (P5, P50, P95)"])

opciones = {"displaylogo": False}
col1, col2 = st.columns([3, 2])
col1.plotly_chart(graficos.abanico(sim.percentiles((5, 25, 50, 75, 95)), sim.trayectorias[:N_MUESTRA],
                                   sim.valor_inicial, moneda, modo), width="stretch", config=opciones)
col2.plotly_chart(graficos.histograma_final(sim.valores_finales, r, (extremos["P1"], extremos["P99"]),
                                            moneda, modo), width="stretch", config=opciones)

col1, col2 = st.columns([3, 2])
with col1:
    st.subheader("Interpretación")
    st.success(sim.interpretacion().replace("\n", "  \n"), icon=":material/lightbulb:")
with col2:
    st.subheader("Parámetros usados")
    p = sim.parametros
    st.dataframe(pd.DataFrame({
        "Peso": [porcentaje(p["pesos"][a]) for a in res.config.activos],
        "Retorno log. anual": [porcentaje(p["retorno"][a]) for a in res.config.activos],
        "Volatilidad anual": [porcentaje(p["volatilidad"][a]) for a in res.config.activos],
    }, index=list(res.config.activos)), width="stretch")
    origen = "estimados con el histórico" if res.config.retorno is None and res.config.volatilidad is None \
        else "con supuestos propios"
    st.caption(f"{numero(p['n_sims'], 0)} escenarios · {p['horizonte']} días de mercado · nu = {p['nu']:g} · "
               f"semilla {p['semilla']} · valor inicial {dinero(p['v0'], moneda)} · parámetros {origen}. "
               "Correlación histórica entre activos; comprar y mantener sin rebalanceo.")

st.subheader("Comparador de colas")
st.markdown(f"La misma cartera, con la misma semilla y la misma volatilidad, simulada con "
            f"**nu = {res.config.nu:g}** y con **nu = {NU_CASI_NORMAL}** (prácticamente normal).")
horizonte = res.config.horizonte
dias = [d for d in (1, 5, 21) if d < horizonte] + [horizonte]
dia = st.segmented_control(
    "Día del horizonte que se compara", dias, default=dias[0], key="dia_colas",
    format_func=lambda d: {1: "1 día", 5: "5 días (1 semana)", 21: "21 días (1 mes)"}.get(d, f"{d} días (final)"),
) or dias[0]
NIVELES = (0.1, 1, 5, 50, 95, 99, 99.9)
cola_t = sim.percentiles(NIVELES).iloc[dia]
cola_n = normal.percentiles(NIVELES).iloc[dia]
col1, col2 = st.columns([3, 2])
limites = (min(cola_t["P0.1"], cola_n["P0.1"]), max(cola_t["P99.9"], cola_n["P99.9"]))
col1.plotly_chart(graficos.comparador_colas(sim.trayectorias[:, dia], normal.trayectorias[:, dia], res.config.nu,
                                            NU_CASI_NORMAL, limites, moneda, dia, modo),
                  width="stretch", config=opciones)
with col2:
    comparacion = pd.DataFrame({
        f"nu = {res.config.nu:g}": [dinero(v, moneda) for v in cola_t],
        f"nu = {NU_CASI_NORMAL}": [dinero(v, moneda) for v in cola_n],
    }, index=[n.replace(".", ",") for n in cola_t.index])
    st.dataframe(comparacion, width="stretch")
st.caption(
    "Cómo leerlo: con nu bajo, en un día hay a la vez más días tranquilos y más días extremos "
    "(P0,1 y P99,9 más alejados). A horizontes largos, la suma de muchos shocks diarios "
    "independientes se parece a una normal (teorema central del límite) y la diferencia casi "
    "desaparece: las colas gruesas importan sobre todo para el riesgo a corto plazo, como el VaR diario.")
componentes.glosario()
