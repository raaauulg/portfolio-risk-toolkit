"""Barra lateral: presets de un clic y configuración guiada en tres pasos.

Los widgets guardan su valor en st.session_state (claves w_*). Nada se calcula al
mover un control: solo al pulsar «Calcular» (o un preset) se fija
st.session_state["config_aplicada"], que es lo que leen las páginas.
"""

from datetime import date, timedelta
import math

import streamlit as st

from app import datos
from app.configuracion import BENCHMARKS, MAX_ACTIVOS, MAX_ESCENARIOS, PRESETS, Configuracion
from app.formato import porcentaje
from app.textos import AYUDA
from app.universos import NOMBRES, UNIVERSOS

PRIMERA = date(2021, 1, 4)   # primera y última sesión de la instantánea
ULTIMA = date(2025, 12, 31)
HORIZONTES = {21: "1 mes", 63: "3 meses", 126: "6 meses", 252: "1 año", 504: "2 años", 756: "3 años"}
_SIN_BENCHMARK = "ninguno"

_POR_DEFECTO = {
    "w_modo": "instantanea", "w_activos": [], "w_tickers": "AAPL, MSFT",
    "w_desde": PRIMERA, "w_hasta": ULTIMA, "w_benchmark": "^GSPC", "w_nombre": "Mi cartera",
    "w_n_sims": 5_000, "w_horizonte": 252, "w_retorno_tipo": "Histórico", "w_retorno": 6.0,
    "w_vol_tipo": "Histórica", "w_vol": 20.0, "w_nu": 5.0, "w_semilla": 42, "w_v0": 10_000.0,
    "w_tasa": 0.0, "w_nivel_var": 0.95,
}


def inicializar() -> None:
    """Valores iniciales de los widgets (solo la primera vez en la sesión)."""
    for clave, valor in _POR_DEFECTO.items():
        st.session_state.setdefault(clave, valor)
    st.session_state.setdefault("config_aplicada", None)


def _activos_elegidos() -> list[str]:
    if st.session_state["w_modo"] == "directo":
        partes = [t.strip().upper() for t in st.session_state["w_tickers"].split(",")]
        return [t for t in partes if t]
    return list(st.session_state["w_activos"])


def construir_config() -> Configuracion:
    """Configuración a partir de los widgets. No valida: eso lo hace el toolkit al calcular."""
    s = st.session_state
    activos = _activos_elegidos()
    return Configuracion(
        modo=s["w_modo"], activos=tuple(activos),
        pesos=tuple(float(s.get(f"w_peso_{a}", 0.0)) / 100 for a in activos),
        inicio=s["w_desde"].isoformat(), fin=(s["w_hasta"] + timedelta(days=1)).isoformat(),
        benchmark=None if s["w_benchmark"] == _SIN_BENCHMARK else s["w_benchmark"],
        n_sims=int(s["w_n_sims"]), horizonte=int(s["w_horizonte"]),
        retorno=None if s["w_retorno_tipo"] == "Histórico" else s["w_retorno"] / 100,
        volatilidad=None if s["w_vol_tipo"] == "Histórica" else s["w_vol"] / 100,
        nu=float(s["w_nu"]), semilla=int(s["w_semilla"]), v0=float(s["w_v0"]),
        tasa_libre=s["w_tasa"] / 100, nivel_var=float(s["w_nivel_var"]),
        nombre=s["w_nombre"].strip() or "Mi cartera",
    )


def aplicar_preset(clave: str) -> None:
    """Copia el preset a los widgets y lo deja aplicado (se usa como callback)."""
    c = PRESETS[clave].config
    s = st.session_state
    s.update({
        "w_modo": c.modo, "w_activos": list(c.activos), "w_nombre": c.nombre,
        # Dentro del rango de la instantánea (como hace el selector al pintarse), para que la
        # configuración aplicada coincida con la de los widgets y no salte «cambios sin aplicar».
        "w_desde": max(date.fromisoformat(c.inicio), PRIMERA),
        "w_hasta": min(date.fromisoformat(c.fin) - timedelta(days=1), ULTIMA),
        "w_benchmark": c.benchmark or _SIN_BENCHMARK, "w_n_sims": c.n_sims, "w_horizonte": c.horizonte,
        "w_retorno_tipo": "Histórico" if c.retorno is None else "Supuesto propio",
        "w_vol_tipo": "Histórica" if c.volatilidad is None else "Supuesto propio",
        "w_nu": c.nu, "w_semilla": c.semilla, "w_v0": c.v0, "w_tasa": c.tasa_libre * 100,
        "w_nivel_var": c.nivel_var,
    })
    for activo, peso in zip(c.activos, c.pesos):
        s[f"w_peso_{activo}"] = peso * 100
    s["preset_activo"] = clave
    s["config_aplicada"] = construir_config()


def _pesos_iguales() -> None:
    activos = _activos_elegidos()
    for activo in activos:
        st.session_state[f"w_peso_{activo}"] = 100 / len(activos)


def _aplicar() -> None:
    st.session_state["preset_activo"] = None
    st.session_state["config_aplicada"] = construir_config()


def _etiqueta_activo(ticker: str) -> str:
    return f"{ticker} · {NOMBRES.get(ticker, ticker)}"


def dibujar() -> None:
    """Pinta la barra lateral completa."""
    s = st.session_state
    barra = st.sidebar
    barra.markdown("### :material/monitoring: Analizador de carteras")
    barra.caption("Toolkit MIAX B1-T1 · capa de presentación")

    barra.markdown("**Presets de un clic**")
    for clave, preset in PRESETS.items():
        barra.button(preset.titulo, key=f"preset_{clave}", help=preset.descripcion, width="stretch",
                     type="primary" if clave == "demo" else "secondary",
                     on_click=aplicar_preset, args=(clave,))

    # ① Datos
    barra.markdown("---\n**① Datos**")
    barra.radio("Modo de datos", ["instantanea", "directo"], key="w_modo", horizontal=True,
                format_func={"instantanea": "Instantánea", "directo": "En directo"}.get, help=AYUDA["modo"])
    if s["w_modo"] == "instantanea":
        disponibles, _ = datos.instantanea()
        opciones = [t for u in UNIVERSOS.values() for t in u.acciones if t in disponibles]
        barra.multiselect("Activos", opciones, key="w_activos", format_func=_etiqueta_activo,
                          max_selections=MAX_ACTIVOS, help=AYUDA["activos"],
                          placeholder="Elige activos de una sola moneda")
        limites = dict(min_value=PRIMERA, max_value=ULTIMA)
        for clave in ("w_desde", "w_hasta"):  # al volver del modo directo, dentro del rango
            s[clave] = min(max(s[clave], PRIMERA), ULTIMA)
    else:
        barra.text_input("Tickers de Yahoo Finance", key="w_tickers", help=AYUDA["tickers"])
        limites = dict(min_value=date(2000, 1, 1), max_value=date.today())
    # Una fecha por fila: en dos columnas no cabe dd/mm/aaaa en la barra lateral.
    barra.date_input("Desde", key="w_desde", format="DD/MM/YYYY", help=AYUDA["desde"], **limites)
    barra.date_input("Hasta", key="w_hasta", format="DD/MM/YYYY", help=AYUDA["hasta"], **limites)
    barra.selectbox("Benchmark", [_SIN_BENCHMARK, *BENCHMARKS], key="w_benchmark",
                    format_func=lambda b: "Sin benchmark" if b == _SIN_BENCHMARK else BENCHMARKS[b],
                    help=AYUDA["benchmark"])

    # ② Cartera
    barra.markdown("---\n**② Cartera**")
    barra.text_input("Nombre de la cartera", key="w_nombre")
    activos = _activos_elegidos()
    if not activos:
        barra.caption("Elige al menos un activo en el paso ①.")
    for activo in activos:
        s.setdefault(f"w_peso_{activo}", 0.0)
        barra.number_input(f"{activo} (%)", min_value=0.0, max_value=100.0, step=0.5, format="%.2f",
                           key=f"w_peso_{activo}", help=AYUDA["pesos"])
    if activos:
        barra.button("Pesos iguales", on_click=_pesos_iguales, icon=":material/balance:")
        suma = sum(float(s.get(f"w_peso_{a}", 0.0)) for a in activos)
        if math.isclose(suma, 100, abs_tol=1e-4):
            barra.success(f"Suma: {porcentaje(suma / 100)}", icon=":material/check_circle:")
        else:
            barra.warning(f"Suma: {porcentaje(suma / 100)}. Los pesos deben sumar 100 %.",
                          icon=":material/error:")

    # ③ Simulación
    barra.markdown("---\n**③ Simulación y métricas**")
    barra.number_input("Escenarios", min_value=500, max_value=MAX_ESCENARIOS, step=500,
                       key="w_n_sims", help=AYUDA["n_sims"])
    barra.select_slider("Horizonte (días de mercado)", options=list(HORIZONTES), key="w_horizonte",
                        format_func=lambda d: f"{d} · {HORIZONTES[d]}", help=AYUDA["horizonte"])
    barra.radio("Retorno anual", ["Histórico", "Supuesto propio"], key="w_retorno_tipo",
                horizontal=True, help=AYUDA["retorno"])
    if s["w_retorno_tipo"] != "Histórico":
        barra.number_input("Retorno logarítmico anual (%)", min_value=-50.0, max_value=50.0, step=0.5,
                           key="w_retorno")
    barra.radio("Volatilidad anual", ["Histórica", "Supuesto propio"], key="w_vol_tipo",
                horizontal=True, help=AYUDA["volatilidad"])
    if s["w_vol_tipo"] != "Histórica":
        barra.number_input("Volatilidad anual (%)", min_value=0.0, max_value=150.0, step=0.5, key="w_vol")
    col1, col2 = barra.columns(2)
    col1.number_input("nu (colas)", min_value=2.1, max_value=200.0, step=0.5, key="w_nu", help=AYUDA["nu"])
    col2.number_input("Semilla", min_value=0, step=1, key="w_semilla", help=AYUDA["semilla"])
    barra.number_input("Valor inicial", min_value=1.0, step=1_000.0, format="%.0f", key="w_v0",
                       help=AYUDA["v0"])
    col1, col2 = barra.columns(2)
    col1.number_input("Tasa libre (%)", min_value=0.0, max_value=20.0, step=0.25, format="%.2f",
                      key="w_tasa", help=AYUDA["tasa_libre"])
    col2.selectbox("Nivel VaR", [0.90, 0.95, 0.99], key="w_nivel_var",
                   format_func=lambda n: porcentaje(n, 0), help=AYUDA["nivel_var"])

    barra.button("Calcular", key="calcular", type="primary", width="stretch", on_click=_aplicar,
                 icon=":material/play_arrow:", help=AYUDA["calcular"])
    aplicada = s.get("config_aplicada")
    if aplicada is not None and aplicada != construir_config():
        barra.info("Hay cambios sin aplicar: pulsa **Calcular**.", icon=":material/pending:")
