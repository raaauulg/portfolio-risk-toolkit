"""Extracción de precios bursátiles con Yahoo Finance (apartado 4.2)."""

from collections.abc import Mapping
from datetime import date

import pandas as pd
import yfinance as yf

from .modelos import SeriePrecios


def descargar_serie(
    ticker: str,
    inicio: str,
    fin: str,
    tipo_activo: str = "accion",
    moneda: str | None = None,
) -> SeriePrecios:
    """Descarga cierres diarios ajustados y crea una SeriePrecios.

    Las fechas tienen formato AAAA-MM-DD; fin es exclusivo.
    La moneda indicada tiene prioridad; si falta, se consultan los metadatos
    y después fast_info. Si ambos fallan, se conserva moneda=None.
    """
    if not isinstance(ticker, str) or not ticker.strip():
        raise ValueError("El ticker debe ser un texto no vacío.")
    ticker = ticker.strip().upper()
    if not isinstance(tipo_activo, str) or not tipo_activo.strip():
        raise ValueError("El tipo de activo debe ser un texto no vacío.")
    if moneda is not None and (not isinstance(moneda, str) or not moneda.strip()):
        raise ValueError("La moneda debe ser un texto no vacío o None.")
    try:
        fecha_inicio = date.fromisoformat(inicio)
        fecha_fin = date.fromisoformat(fin)
        if inicio != fecha_inicio.isoformat() or fin != fecha_fin.isoformat():
            raise ValueError("Formato de fecha no admitido.")
    except (TypeError, ValueError) as error:
        raise ValueError("Las fechas deben tener formato AAAA-MM-DD.") from error
    if fecha_inicio >= fecha_fin:
        raise ValueError("La fecha de inicio debe ser anterior a la fecha final.")

    instrumento = yf.Ticker(ticker)
    try:
        datos = instrumento.history(
            start=inicio, end=fin, interval="1d", auto_adjust=True
        )
    except Exception as error:
        raise RuntimeError(f"No se pudo descargar {ticker} desde Yahoo Finance.") from error

    if not isinstance(datos, pd.DataFrame) or datos.empty or "Close" not in datos.columns:
        raise ValueError(f"Yahoo Finance no devolvió precios de cierre para {ticker}.")

    precios = datos["Close"].copy()
    if (not isinstance(precios, pd.Series) or not pd.api.types.is_numeric_dtype(precios.dtype)
            or pd.api.types.is_bool_dtype(precios.dtype) or pd.api.types.is_complex_dtype(precios.dtype)):
        raise ValueError(f"Yahoo Finance devolvió precios no numéricos reales para {ticker}.")
    if not isinstance(precios.index, pd.DatetimeIndex):
        raise ValueError(f"Yahoo Finance devolvió fechas inválidas para {ticker}.")
    if precios.index.tz is not None:
        precios.index = precios.index.tz_localize(None)
    precios.index = precios.index.normalize()
    precios = precios[precios.index.notna()].dropna().sort_index()
    precios = precios.loc[(precios.index >= pd.Timestamp(fecha_inicio))
                          & (precios.index < pd.Timestamp(fecha_fin))]
    if precios.index.has_duplicates:
        raise ValueError(f"Yahoo Finance devolvió fechas duplicadas para {ticker}.")
    if (precios <= 0).any():
        raise ValueError(f"Yahoo Finance devolvió precios no positivos para {ticker}.")

    # Un fallo al leer los metadatos no debe impedir devolver los precios.
    if moneda is None:
        try:
            metadatos = instrumento.get_history_metadata()
            if isinstance(metadatos, Mapping):
                valor = metadatos.get("currency")
                if isinstance(valor, str) and valor.strip():
                    moneda = valor.strip().upper()
        except Exception:
            moneda = None

        if moneda is None:
            try:
                valor = instrumento.fast_info["currency"]
                if isinstance(valor, str) and valor.strip():
                    moneda = valor.strip().upper()
            except Exception:
                moneda = None

    return SeriePrecios(
        ticker=ticker,
        precios=precios,
        fuente="Yahoo Finance",
        tipo_activo=tipo_activo,
        moneda=moneda,
        ajuste="indice_precios" if tipo_activo == "indice" else "dividendos_y_splits",
    )


def descargar_series(
    tickers: list[str],
    inicio: str,
    fin: str,
    tipos: dict[str, str] | None = None,
    monedas: dict[str, str] | None = None,
) -> dict[str, SeriePrecios]:
    """Descarga un lote de activos y devuelve {ticker: SeriePrecios}.

    Las claves de tipos y monedas deben ir en mayúsculas, como los tickers ya
    normalizados. Si un activo falla, se propaga su excepción: nunca se
    devuelve un lote incompleto.
    """
    if not isinstance(tickers, list) or not tickers:
        raise ValueError("Debes facilitar una lista no vacía de tickers.")
    if any(not isinstance(ticker, str) or not ticker.strip() for ticker in tickers):
        raise ValueError("Todos los tickers deben ser textos no vacíos.")
    simbolos = [ticker.strip().upper() for ticker in tickers]
    if len(simbolos) != len(set(simbolos)):
        raise ValueError("La lista contiene tickers duplicados.")

    tipos = {} if tipos is None else tipos
    monedas = {} if monedas is None else monedas
    for nombre, opciones in (("tipos", tipos), ("monedas", monedas)):
        if not isinstance(opciones, dict) or set(opciones) - set(simbolos):
            raise ValueError(f"{nombre} debe ser un diccionario con tickers del lote en mayúsculas.")
        if any(not isinstance(v, str) or not v.strip() for v in opciones.values()):
            raise ValueError(f"Los valores de {nombre} deben ser textos no vacíos.")
    resultado: dict[str, SeriePrecios] = {}
    for ticker in simbolos:
        resultado[ticker] = descargar_serie(
            ticker=ticker,
            inicio=inicio,
            fin=fin,
            tipo_activo=tipos.get(ticker, "accion"),
            moneda=monedas.get(ticker),
        )
    return resultado
