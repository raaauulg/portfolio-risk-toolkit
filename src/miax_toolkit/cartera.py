"""Modelo de cartera de inversión (apartado 4.3)."""

from dataclasses import dataclass
from math import isclose, isfinite

import pandas as pd

from .limpieza2 import alinear_precios, limpiar_precios
from .modelos import SeriePrecios
from .montecarlo import SimulationResult, simular_activo, simular_cartera
from .reportes import GRAFICOS, SECCIONES, generar_plots, generar_report

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
        v0: float | None = None,
        semilla: int | None = 42,
        activo: str | None = None,
    ) -> SimulationResult:
        """Simula la cartera completa o, si se indica activo, solo ese activo.

        Los precios se limpian y alinean antes de simular. El resultado se
        dibuja con resultado.plot() y se explica con resultado.interpretacion().
        """
        opciones = dict(n_sims=n_sims, horizonte=horizonte, retorno=retorno,
                        volatilidad=volatilidad, nu=nu, semilla=semilla)
        if activo is not None:
            precios = self.obtener_precios()
            if activo not in precios:
                raise ValueError(f"El activo {activo!r} no está en la cartera.")
            serie, _ = limpiar_precios(precios[activo], nombre=activo)
            return simular_activo(serie.rename(activo), v0=v0, **opciones)

        precios, _ = alinear_precios(self.obtener_precios())
        return simular_cartera(precios, self.obtener_pesos(), v0=100.0 if v0 is None else v0,
                               nombre=self.nombre, **opciones)

    def report(
        self,
        secciones=SECCIONES,
        tasa_libre: float = 0.0,
        nivel_var: float = 0.95,
        benchmark: pd.Series | None = None,
        simulacion: SimulationResult | None = None,
        umbrales: dict | None = None,
        ruta=None,
    ) -> str:
        """Informe en Markdown con métricas, diagnóstico y advertencias de riesgo.

        Limpia y alinea los precios y delega en reportes.generar_report. Para
        incluir el Monte Carlo, pasar simulacion=cartera.monte_carlo().
        """
        precios, diagnostico = alinear_precios(self.obtener_precios())
        return generar_report(
            precios, self.obtener_pesos(), nombre=self.nombre, secciones=secciones,
            tasa_libre=tasa_libre, nivel_var=nivel_var, benchmark=benchmark,
            simulacion=simulacion, diagnostico=diagnostico,
            monedas=self.obtener_monedas(), umbrales=umbrales, ruta=ruta,
        )

    def plots_report(
        self,
        graficos=GRAFICOS,
        benchmark: pd.Series | None = None,
        ventana_volatilidad: int = 63,
        mostrar: bool = True,
        carpeta=None,
    ) -> dict:
        """Gráficos de rendimiento, correlaciones, evolución y riesgo de la cartera."""
        precios, _ = alinear_precios(self.obtener_precios())
        return generar_plots(
            precios, self.obtener_pesos(), nombre=self.nombre, graficos=graficos,
            benchmark=benchmark, ventana_volatilidad=ventana_volatilidad,
            mostrar=mostrar, carpeta=carpeta,
        )