"""Extracción de precios bursátiles con Yahoo Finance (apartado 4.2)."""

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

    instrumento = yf.Ticker(ticker)
    try:
        datos = instrumento.history(
            start=inicio, end=fin, interval="1d", auto_adjust=True
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

    # Si no se indica la moneda, intenta conocerla por la propia fuente.
    # La ausencia de metadatos no debe impedir recuperar los precios.
    if moneda is None:
        try:
            metadatos = instrumento.get_history_metadata()
            if isinstance(metadatos, dict):
                valor = metadatos.get("currency")
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
    )


def descargar_series(
    tickers: list[str],
    inicio: str,
    fin: str,
    tipos: dict[str, str] | None = None,
    monedas: dict[str, str] | None = None,
) -> dict[str, SeriePrecios]:
    """Descarga un lote de activos y devuelve {ticker: SeriePrecios}.

    Los símbolos de los diccionarios opcionales se escriben en mayúsculas.
    Se detiene con un error si alguno de los activos no puede descargarse;
    no devuelve una cartera incompleta sin avisar.
    """
    if not isinstance(tickers, list) or not tickers:
        raise ValueError("Debes facilitar una lista no vacía de tickers.")
    if any(not isinstance(ticker, str) or not ticker.strip() for ticker in tickers):
        raise ValueError("Todos los tickers deben ser textos no vacíos.")
    simbolos = [ticker.strip().upper() for ticker in tickers]
    if len(simbolos) != len(set(simbolos)):
        raise ValueError("La lista contiene tickers duplicados.")

    tipos = tipos or {}
    monedas = monedas or {}
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
