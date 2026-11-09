"""Carga de datos (instantánea local o en directo con el toolkit) y caché de Streamlit.

Es la única frontera entre la app y la caché: las funciones puras (leer_instantanea,
recortar) no dependen de Streamlit; las envolturas con st.cache_* evitan repetir
descargas, simulaciones y figuras en cada interacción.
"""

from dataclasses import replace
from datetime import date
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

from miax_toolkit import SeriePrecios, descargar_serie, descargar_series, descargar_sp500_fred

from app.analisis import Resultados, calcular
from app.configuracion import Configuracion

CARPETA_INSTANTANEA = Path(__file__).resolve().parents[1] / "data" / "sample"


# ---------- Funciones puras ----------

def leer_instantanea(carpeta: Path = CARPETA_INSTANTANEA) -> tuple[dict[str, SeriePrecios], pd.DataFrame]:
    """Lee los CSV de data/sample y devuelve ({ticker: SeriePrecios}, metadatos).

    La fuente se marca como instantánea, con su fecha de descarga.
    """
    metadatos = pd.read_csv(carpeta / "series.csv")
    series: dict[str, SeriePrecios] = {}
    for universo, filas in metadatos.groupby("universo", sort=False):
        precios = pd.read_csv(carpeta / f"precios_{universo}.csv", parse_dates=["fecha"])
        for _, meta in filas.iterrows():
            valores = precios.loc[precios["ticker"] == meta["ticker"]].set_index("fecha")["cierre"]
            valores.index = pd.DatetimeIndex(valores.index, name=None)
            descarga = date.fromisoformat(meta["fecha_descarga"]).strftime("%d/%m/%Y")
            series[meta["ticker"]] = SeriePrecios(
                ticker=meta["ticker"], precios=valores.astype(float),
                fuente=f"{meta['fuente']} (instantánea {descarga})",
                tipo_activo=meta["tipo_activo"], moneda=meta["moneda"], frecuencia=meta["frecuencia"],
                unidad=meta["unidad"], ajuste=meta["ajuste"],
            )
    return series, metadatos.set_index("ticker")


def recortar(serie: SeriePrecios, inicio: str, fin: str) -> SeriePrecios:
    """Nueva SeriePrecios con las fechas de [inicio, fin): el toolkit recalcula sus estadísticos."""
    precios = serie.precios.loc[(serie.precios.index >= inicio) & (serie.precios.index < fin)]
    if len(precios) < 2:
        raise ValueError(f"{serie.ticker}: no hay al menos dos precios entre {inicio} y {fin} (fin exclusivo).")
    return replace(serie, precios=precios)


# ---------- Cachés ----------

@st.cache_data(show_spinner=False)
def instantanea() -> tuple[dict[str, SeriePrecios], pd.DataFrame]:
    """La instantánea se lee una sola vez por proceso."""
    return leer_instantanea()


@st.cache_data(show_spinner=False, ttl=3600, max_entries=16)
def descargar_en_directo(activos: tuple[str, ...], inicio: str, fin: str,
                         benchmark: str | None) -> tuple[dict[str, SeriePrecios], SeriePrecios | None]:
    """Descarga con los extractores del toolkit. Una hora de caché para no repetir llamadas."""
    tipos = {ticker: "indice" for ticker in activos if ticker.startswith("^")}
    series = descargar_series(list(activos), inicio, fin, tipos=tipos)
    referencia = None
    if benchmark == "^GSPC":
        referencia = descargar_sp500_fred(inicio, fin)
    elif benchmark:
        referencia = descargar_serie(benchmark, inicio, fin, tipo_activo="indice")
    return series, referencia


class ErrorDeDatos(ValueError):
    """Los datos pedidos no existen o la consulta no es válida (ticker, fechas, rango sin sesiones).

    Envuelve los ValueError que lanza el toolkit al obtener los datos para que la
    interfaz los distinga de los errores de validación de la cartera. Los fallos de
    red o del proveedor siguen siendo RuntimeError y no pasan por aquí.
    """


def cargar_series(config: Configuracion) -> tuple[dict[str, SeriePrecios], SeriePrecios | None]:
    """SeriePrecios de los activos y del benchmark según el modo elegido.

    ValueError del toolkit -> ErrorDeDatos (mismo mensaje); RuntimeError se propaga tal cual.
    """
    try:
        return _cargar_series(config)
    except ErrorDeDatos:
        raise
    except ValueError as error:
        raise ErrorDeDatos(str(error)) from error


def _cargar_series(config: Configuracion) -> tuple[dict[str, SeriePrecios], SeriePrecios | None]:
    if config.modo == "directo":
        return descargar_en_directo(config.activos, config.inicio, config.fin, config.benchmark)
    disponibles, _ = instantanea()
    faltan = [t for t in (*config.activos, config.benchmark) if t and t not in disponibles]
    if faltan:
        raise ValueError(f"La instantánea no contiene {', '.join(faltan)}. Usa el modo En directo.")
    series = {t: recortar(disponibles[t], config.inicio, config.fin) for t in config.activos}
    referencia = None
    if config.benchmark:
        referencia = recortar(disponibles[config.benchmark], config.inicio, config.fin)
    return series, referencia


@st.cache_resource(show_spinner=False, max_entries=4)
def resultados(config: Configuracion) -> Resultados:
    """Cartera, informe y las dos simulaciones de una configuración.

    cache_resource (no cache_data): devuelve el mismo objeto sin copiarlo; las
    trayectorias ocupan decenas de MB y copiarlas en cada interacción sería lento.
    Las páginas solo lo leen.
    """
    series, referencia = cargar_series(config)
    return calcular(config, series, referencia)


@st.cache_data(show_spinner=False, max_entries=8)
def figuras_toolkit_png(config: Configuracion) -> dict[str, bytes]:
    """PNG de las figuras de matplotlib del propio toolkit: plots_report() y SimulationResult.plot()."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    res = resultados(config)
    figuras = res.cartera.plots_report(
        benchmark=None if res.benchmark is None else res.benchmark.precios, mostrar=False)
    figuras["montecarlo"] = res.simulacion.plot(mostrar=False)
    imagenes = {}
    for nombre, figura in figuras.items():
        bufer = BytesIO()
        figura.savefig(bufer, format="png", dpi=150)
        plt.close(figura)
        imagenes[nombre] = bufer.getvalue()
    return imagenes
