"""Modelo de cartera de inversión (apartado 4.3)."""

from dataclasses import dataclass
from math import isclose, isfinite

import pandas as pd

from .modelos import SeriePrecios


@dataclass
class Cartera:
    """Agrupa series de precios y sus ponderaciones."""

    nombre: str
    series: list[SeriePrecios]
    pesos: dict[str, float]

    def __post_init__(self) -> None:
        if not self.nombre.strip() or not self.series:
            raise ValueError("La cartera necesita un nombre y al menos un activo.")
        if not all(isinstance(serie, SeriePrecios) for serie in self.series):
            raise ValueError("Los activos deben ser objetos SeriePrecios.")

        tickers = [serie.ticker for serie in self.series]
        if len(tickers) != len(set(tickers)):
            raise ValueError("No puede haber activos con el mismo ticker.")
        if set(self.pesos) != set(tickers):
            raise ValueError("Debe existir exactamente un peso por activo.")

        try:
            pesos = {ticker: float(peso) for ticker, peso in self.pesos.items()}
        except (TypeError, ValueError) as error:
            raise ValueError("Los pesos deben ser numéricos.") from error
        if not all(isfinite(peso) for peso in pesos.values()):
            raise ValueError("Los pesos deben ser finitos.")
        if not isclose(sum(pesos.values()), 1.0, abs_tol=1e-6):
            raise ValueError("Los pesos de la cartera deben sumar 1.")
        self.pesos = pesos

    def obtener_precios(self) -> dict[str, pd.Series]:
        """Devuelve {ticker: serie de precios}, para los módulos de análisis."""
        return {serie.ticker: serie.precios.copy() for serie in self.series}

    def obtener_pesos(self) -> dict[str, float]:
        """Devuelve las ponderaciones de los activos."""
        return self.pesos.copy()
