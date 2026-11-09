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
import numpy as np


@dataclass
class SerieIndicador:
    """Indicador numérico con fechas, procedencia, frecuencia y unidades."""

    indicador: str
    pais: str
    valores: pd.Series
    fuente: str = "Banco Mundial"
    frecuencia: str = "anual"
    unidad: str = "no especificada"

    def __post_init__(self):
        if any(not isinstance(v, str) or not v.strip() for v in (self.indicador, self.pais, self.fuente, self.frecuencia, self.unidad)):
            raise ValueError("Los metadatos del indicador deben ser textos no vacíos.")
        if not isinstance(self.valores, pd.Series) or self.valores.empty:
            raise ValueError("El indicador necesita observaciones.")
        if not isinstance(self.valores.index, pd.DatetimeIndex) or self.valores.index.hasnans or self.valores.index.has_duplicates:
            raise ValueError("Las fechas del indicador deben ser válidas y únicas.")
        if (not pd.api.types.is_numeric_dtype(self.valores.dtype)
                or pd.api.types.is_bool_dtype(self.valores.dtype)
                or pd.api.types.is_complex_dtype(self.valores.dtype)):
            raise ValueError("El indicador debe ser numérico real.")
        if self.valores.isna().any() or not np.isfinite(self.valores.to_numpy()).all():
            raise ValueError("El indicador debe contener valores finitos.")
        self.valores = self.valores.astype(float).sort_index().copy()
        if self.valores.index.tz is not None:
            self.valores.index = self.valores.index.tz_localize(None)
        self.valores.index = self.valores.index.normalize()
        if self.valores.index.has_duplicates:
            raise ValueError("Las fechas del indicador deben ser únicas por día.")
        self.valores.name = self.indicador


def descargar_indicador(
    pais: str, indicador: str, inicio: int, fin: int, unidad: str | None = None
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
        with urlopen(url, timeout=30) as respuesta:
            datos = json.loads(respuesta.read().decode("utf-8"))
    except (OSError, ValueError) as error:
        raise RuntimeError("No se pudo obtener el indicador del Banco Mundial.") from error

    if not isinstance(datos, list) or len(datos) != 2 or not isinstance(datos[1], list):
        raise ValueError("La API del Banco Mundial ha devuelto una respuesta inesperada.")

    observaciones = []
    for fila in datos[1]:
        if (not isinstance(fila, dict) or "value" not in fila
                or not re.fullmatch(r"\d{4}", str(fila.get("date", "")))):
            raise ValueError("El Banco Mundial devolvió una observación anual inválida.")
        anio = int(fila["date"])
        if not inicio <= anio <= fin or fila["value"] is None:
            continue
        try:
            if isinstance(fila["value"], bool):
                raise ValueError("Un booleano no es un indicador.")
            valor = float(fila["value"])
        except (TypeError, ValueError) as error:
            raise ValueError("El Banco Mundial devolvió un valor no numérico.") from error
        observaciones.append((pd.Timestamp(f"{anio}-12-31"), valor))
    if not observaciones:
        raise ValueError("No hay datos del indicador para el país y periodo solicitados.")

    fechas, valores = zip(*sorted(observaciones))
    serie = pd.Series(valores, index=pd.DatetimeIndex(fechas), name=indicador, dtype=float)
    unidad = unidad or ("USD corrientes" if indicador == "NY.GDP.MKTP.CD" else "no especificada")
    return SerieIndicador(indicador=indicador, pais=pais, valores=serie, unidad=unidad)
