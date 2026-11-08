"""Indicadores macroeconómicos del Banco Mundial (apartado 4.2).

Las observaciones anuales no son precios bursátiles y no se incorporan
directamente a una Cartera.
"""

from dataclasses import dataclass
import json
import re
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd


@dataclass
class SerieIndicador:
    """Serie anual de un indicador económico, con su procedencia."""

    indicador: str
    pais: str
    valores: pd.Series
    fuente: str = "Banco Mundial"
    frecuencia: str = "anual"


def descargar_indicador(
    pais: str, indicador: str, inicio: int, fin: int
) -> SerieIndicador:
    """Obtiene un indicador anual del Banco Mundial sin clave API.

    Ejemplo: PIB nominal de España (ESP, NY.GDP.MKTP.CD).
    """
    if not isinstance(pais, str) or not re.fullmatch(r"[A-Za-z]{2,3}", pais):
        raise ValueError("El país debe ser un código de dos o tres letras.")
    if not isinstance(indicador, str) or not re.fullmatch(r"[A-Za-z0-9._-]+", indicador):
        raise ValueError("El código del indicador es inválido.")
    if (not isinstance(inicio, int) or isinstance(inicio, bool)
            or not isinstance(fin, int) or isinstance(fin, bool)
            or inicio < 1900 or fin > 2100 or inicio > fin):
        raise ValueError("El intervalo anual no es válido.")

    pais = pais.upper()
    indicador = indicador.upper()
    parametros = urlencode({
        "format": "json", "date": f"{inicio}:{fin}", "per_page": "500"
    })
    url = f"https://api.worldbank.org/v2/country/{pais}/indicator/{indicador}?{parametros}"

    try:
        with urlopen(url, timeout=15) as respuesta:
            datos = json.loads(respuesta.read().decode("utf-8"))
    except (OSError, ValueError) as error:
        raise RuntimeError("No se pudo obtener el indicador del Banco Mundial.") from error

    if not isinstance(datos, list) or len(datos) != 2 or not isinstance(datos[1], list):
        raise ValueError("La API del Banco Mundial ha devuelto una respuesta inesperada.")

    observaciones = [
        (pd.Timestamp(f"{fila['date']}-12-31"), float(fila["value"]))
        for fila in datos[1] if isinstance(fila, dict) and fila.get("value") is not None
    ]
    if not observaciones:
        raise ValueError("No hay datos del indicador para el país y periodo solicitados.")

    fechas, valores = zip(*sorted(observaciones))
    serie = pd.Series(valores, index=pd.DatetimeIndex(fechas), name=indicador, dtype=float)
    return SerieIndicador(indicador=indicador, pais=pais, valores=serie)
