"""Modelo de una serie de precios históricos (apartado 4.3)."""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class SeriePrecios:
    """Precios de un activo con sus metadatos y estadísticos básicos."""

    ticker: str
    precios: pd.Series
    fuente: str
    tipo_activo: str = "accion"
    moneda: str | None = None
    media: float = field(init=False)
    desviacion_tipica: float = field(init=False)

    def __post_init__(self) -> None:
        if (not isinstance(self.ticker, str) or not self.ticker.strip()
                or not isinstance(self.fuente, str) or not self.fuente.strip()):
            raise ValueError("Ticker y fuente no pueden estar vacíos.")
        if not isinstance(self.precios, pd.Series) or self.precios.empty:
            raise ValueError("Los precios deben ser una serie de pandas no vacía.")
        if not isinstance(self.precios.index, pd.DatetimeIndex):
            raise ValueError("Los precios deben tener un índice de fechas.")
        if not pd.api.types.is_numeric_dtype(self.precios.dtype) or pd.api.types.is_bool_dtype(self.precios.dtype):
            raise ValueError("Los precios deben ser numéricos.")

        validos = self.precios.dropna().astype(float)
        if len(validos) < 2 or not np.isfinite(validos.to_numpy()).all():
            raise ValueError("Se necesitan al menos dos precios válidos y finitos.")

        self.precios = self.precios.astype(float).copy()
        self.precios.name = self.ticker
        self.media = float(validos.mean())
        self.desviacion_tipica = float(validos.std(ddof=1))
