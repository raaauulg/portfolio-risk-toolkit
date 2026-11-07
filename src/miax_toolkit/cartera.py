"""Modelo de cartera de inversión (apartado 4.3)."""

from dataclasses import dataclass
from math import isclose, isfinite

import pandas as pd

from .limpieza import alinear_precios
from .modelos import SeriePrecios
from .monte_carlo import SimulationResult, simular_cartera


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

    def obtener_monedas(self) -> dict[str, str] | None:
        """Devuelve las monedas conocidas, o None si no hay información."""
        conocidas = {serie.ticker: serie.moneda for serie in self.series if serie.moneda}
        return conocidas or None

    def monte_carlo(
        self,
        n_sims: int = 10_000,
        horizonte: int = 252,
        retorno=None,
        volatilidad=None,
        nu: float = 5,
        v0: float = 100.0,
        semilla: int | None = 42,
        min_observaciones: int = 30,
    ) -> SimulationResult:
        """Simula la cartera con Monte Carlo (apartado 4.4).

        Fachada: la cartera solo prepara los datos (limpia y alinea sus precios)
        y delega la matemática en monte_carlo.simular_cartera. Parámetros como en
        simular_cartera: retorno y volatilidad anuales (None = histórico), horizonte
        en días de mercado, v0 = valor inicial de la cartera.
        min_observaciones: fechas comunes mínimas para estimar los parámetros.
        """
        tabla, resumen = alinear_precios(self.obtener_precios())
        if len(tabla) < min_observaciones:
            raise ValueError(
                f"La cartera '{self.nombre}' solo tiene {len(tabla)} fechas comunes "
                f"tras limpiar y alinear; se necesitan al menos {min_observaciones} "
                "para estimar retorno, volatilidad y correlación."
            )
        resultado = simular_cartera(
            tabla, self.obtener_pesos(), n_sims=n_sims, horizonte=horizonte,
            retorno=retorno, volatilidad=volatilidad, nu=nu, v0=v0,
            semilla=semilla, nombre=self.nombre,
        )
        resultado.parametros["limpieza"] = resumen
        return resultado
