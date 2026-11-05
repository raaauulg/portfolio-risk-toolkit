"""Descarga de precios históricos desde Yahoo Finance (apartado 4.2)."""

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
    """Descarga cierres diarios ajustados y devuelve una SeriePrecios.

    Las fechas tienen formato AAAA-MM-DD y la fecha final es exclusiva.
    Para un índice, se puede usar ticker='^GSPC', tipo_activo='indice'.
    """
    if not isinstance(ticker, str) or not ticker.strip():
        raise ValueError("El ticker debe ser un texto no vacío.")
    ticker = ticker.strip().upper()
    try:
        fecha_inicio = date.fromisoformat(inicio)
        fecha_fin = date.fromisoformat(fin)
    except (TypeError, ValueError) as error:
        raise ValueError("Las fechas deben tener formato AAAA-MM-DD.") from error
    if fecha_inicio >= fecha_fin:
        raise ValueError("La fecha de inicio debe ser anterior a la fecha final.")

    try:
        datos = yf.Ticker(ticker).history(
            start=inicio,
            end=fin,
            interval="1d",
            auto_adjust=True,
        )
    except Exception as error:
        raise RuntimeError(f"No se pudo descargar {ticker} desde Yahoo Finance.") from error

    if datos is None or datos.empty or "Close" not in datos.columns:
        raise ValueError(f"Yahoo Finance no devolvió precios de cierre para {ticker}.")

    precios = datos["Close"].copy()
    if not isinstance(precios.index, pd.DatetimeIndex):
        raise ValueError(f"Yahoo Finance devolvió fechas inválidas para {ticker}.")
    if precios.index.tz is not None:
        precios.index = precios.index.tz_localize(None)
    precios.index = precios.index.normalize()
    precios = precios.sort_index()

    return SeriePrecios(
        ticker=ticker,
        precios=precios,
        fuente="Yahoo Finance",
        tipo_activo=tipo_activo,
        moneda=moneda,
    )
