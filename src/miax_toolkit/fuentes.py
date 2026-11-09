"""Adaptadores de FRED (CSV público) y BCE (API SDMX), apartado 4.2.

Conservan la frecuencia y las unidades originales. Las fechas finales son
exclusivas, como en el extractor de Yahoo. No interpolan ni convierten divisas.
"""

from datetime import date, timedelta
from io import StringIO
import re

import numpy as np
import pandas as pd
import requests

from .macroeconomia import SerieIndicador
from .modelos import SeriePrecios


def _intervalo(inicio: str, fin: str):
    try:
        primero, ultimo = date.fromisoformat(inicio), date.fromisoformat(fin)
        if inicio != primero.isoformat() or fin != ultimo.isoformat():
            raise ValueError("Formato de fecha no admitido.")
    except (TypeError, ValueError) as error:
        raise ValueError("Las fechas deben tener formato AAAA-MM-DD.") from error
    if primero >= ultimo:
        raise ValueError("El inicio debe ser anterior al fin exclusivo.")
    return primero, ultimo


def _csv(url: str, parametros: dict, fuente: str, periodo: str = "") -> pd.DataFrame:
    """Descarga un CSV distinguiendo fallo de red (RuntimeError) y ausencia de datos (ValueError).

    FRED responde 404 y el BCE un cuerpo vacío cuando no hay observaciones en el
    rango (por ejemplo, un fin de semana); eso no es un problema de conexión.
    """
    try:
        respuesta = requests.get(url, params=parametros, timeout=30)
    except requests.RequestException as error:
        raise RuntimeError(f"No se pudo conectar con {fuente}; comprueba la conexión a Internet.") from error

    sin_datos = (
        f"{fuente} no tiene observaciones para esa serie{periodo}. "
        "Puede que la serie no exista o que el rango no contenga días con dato "
        "(fin de semana, festivo o fechas fuera del histórico disponible)."
    )
    if respuesta.status_code == 404:
        raise ValueError(sin_datos)
    try:
        respuesta.raise_for_status()
    except requests.HTTPError as error:
        raise RuntimeError(
            f"{fuente} respondió con un error HTTP {respuesta.status_code}; inténtalo más tarde."
        ) from error
    # Una respuesta vacía solo significa ausencia de datos si la petición tuvo
    # éxito. Un 429/503 vacío sigue siendo un error del servicio.
    if not respuesta.text.strip():
        raise ValueError(sin_datos)
    try:
        return pd.read_csv(StringIO(respuesta.text))
    except pd.errors.EmptyDataError as error:
        raise ValueError(sin_datos) from error
    except pd.errors.ParserError as error:
        raise RuntimeError(f"{fuente} devolvió una respuesta que no es un CSV válido.") from error


def _periodo(primero: date, ultimo: date) -> str:
    return f" entre {primero.isoformat()} y {ultimo.isoformat()} (fin exclusivo)"


def _normalizar(tabla, columna_fecha, columna_valor, inicio, fin, nombre):
    if columna_fecha not in tabla or columna_valor not in tabla:
        raise ValueError("La fuente devolvió columnas inesperadas.")
    fechas = pd.to_datetime(tabla[columna_fecha], errors="coerce")
    valores = pd.to_numeric(tabla[columna_valor], errors="coerce")
    serie = pd.Series(valores.to_numpy(), index=pd.DatetimeIndex(fechas), name=nombre, dtype=float)
    if serie.index.tz is not None:
        serie.index = serie.index.tz_localize(None)
    serie.index = serie.index.normalize()
    # FRED representa festivos y datos no disponibles como puntos o celdas vacías.
    serie = serie[serie.index.notna() & np.isfinite(serie.to_numpy())]
    if serie.index.has_duplicates:
        raise ValueError("La fuente devolvió observaciones duplicadas para una fecha.")
    serie = serie.loc[(serie.index >= pd.Timestamp(inicio)) & (serie.index < pd.Timestamp(fin))].sort_index()
    if serie.empty:
        raise ValueError("No hay observaciones válidas en el periodo solicitado.")
    return serie


def _fred(indicador, inicio, fin):
    primero, ultimo = _intervalo(inicio, fin)
    if not isinstance(indicador, str) or not re.fullmatch(r"[A-Za-z0-9_]+", indicador):
        raise ValueError("El identificador FRED es inválido.")
    indicador = indicador.upper()
    tabla = _csv("https://fred.stlouisfed.org/graph/fredgraph.csv", {
        "id": indicador, "cosd": primero.isoformat(), "coed": (ultimo - timedelta(days=1)).isoformat(),
    }, "FRED", _periodo(primero, ultimo))
    fecha = "observation_date" if "observation_date" in tabla else "DATE"
    return _normalizar(tabla, fecha, indicador, primero, ultimo, indicador)


def descargar_indicador_fred(indicador: str, inicio: str, fin: str, *,
                              pais: str, frecuencia: str, unidad: str) -> SerieIndicador:
    """Descarga un indicador FRED sin clave, mediante su CSV público.

    El CSV no incluye metadatos: país, frecuencia y unidad deben indicarse
    según la ficha oficial de la serie. Por ejemplo UNRATE, USA, mensual, %.
    """
    if frecuencia not in {"diaria", "semanal", "mensual", "trimestral", "anual"}:
        raise ValueError("La frecuencia del indicador no está reconocida.")
    valores = _fred(indicador, inicio, fin)
    return SerieIndicador(indicador.upper(), pais, valores, "FRED", frecuencia, unidad)


def descargar_sp500_fred(inicio: str, fin: str) -> SeriePrecios:
    """S&P 500 de FRED: cierre diario en puntos, índice de precios sin dividendos.

    Usa el mismo identificador interno ^GSPC que Yahoo. La ficha de FRED ofrece
    una ventana móvil de diez años; el rango efectivo puede ser menor al pedido.
    """
    valores = _fred("SP500", inicio, fin)
    if (valores <= 0).any():
        raise ValueError("FRED devolvió valores no positivos del índice.")
    return SeriePrecios("^GSPC", valores, "FRED", tipo_activo="indice", moneda="USD",
                        unidad="puntos de indice", ajuste="indice_precios")


def descargar_tipo_cambio_bce(moneda: str, inicio: str, fin: str) -> SerieIndicador:
    """Tipo de referencia diario: unidades de moneda por 1 EUR, sin clave API."""
    primero, ultimo = _intervalo(inicio, fin)
    if not isinstance(moneda, str) or not re.fullmatch(r"[A-Za-z]{3}", moneda) or moneda.upper() == "EUR":
        raise ValueError("Indica un código de moneda de tres letras distinto de EUR, por ejemplo USD.")
    moneda = moneda.upper()
    clave = f"D.{moneda}.EUR.SP00.A"
    tabla = _csv(f"https://data-api.ecb.europa.eu/service/data/EXR/{clave}", {
        "startPeriod": primero.isoformat(), "endPeriod": (ultimo - timedelta(days=1)).isoformat(),
        "format": "csvdata",
    }, "BCE", _periodo(primero, ultimo))
    valores = _normalizar(tabla, "TIME_PERIOD", "OBS_VALUE", primero, ultimo, clave)
    if (valores <= 0).any():
        raise ValueError("El BCE devolvió un tipo de cambio no positivo.")
    return SerieIndicador(clave, "zona euro", valores, "BCE", "diaria", f"{moneda} por 1 EUR")
