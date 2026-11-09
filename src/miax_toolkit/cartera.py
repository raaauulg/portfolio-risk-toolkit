"""Modelo de cartera de inversión (apartado 4.3)."""

from dataclasses import dataclass
from math import isclose

import pandas as pd

from .limpieza import alinear_precios, validar_pesos, validar_tabla
from .modelos import SeriePrecios
from .monte_carlo import SimulationResult, simular_cartera
from .reportes import SECCIONES, GRAFICOS, generar_report, generar_plots


@dataclass
class Cartera:
    """Agrupa series de precios y sus ponderaciones."""

    nombre: str
    series: list[SeriePrecios]
    pesos: dict[str, float]

    def __post_init__(self) -> None:
        self._validar_composicion()

    def _validar_composicion(self) -> None:
        """Valida también las listas y pesos que se hayan editado tras crearla."""
        if (not isinstance(self.nombre, str) or not self.nombre.strip()
                or not isinstance(self.series, list) or not self.series):
            raise ValueError("La cartera necesita un nombre y al menos un activo.")
        if not all(isinstance(serie, SeriePrecios) for serie in self.series):
            raise ValueError("Los activos deben ser objetos SeriePrecios.")
        if not isinstance(self.pesos, dict):
            raise ValueError("Los pesos deben ser un diccionario por ticker.")

        tickers = [serie.ticker for serie in self.series]
        if any(not isinstance(t, str) or not t.strip() for t in tickers):
            raise ValueError("Todos los activos deben tener un ticker no vacío.")
        if len(tickers) != len(set(tickers)):
            raise ValueError("No puede haber activos con el mismo ticker.")
        if set(self.pesos) != set(tickers):
            raise ValueError("Debe existir exactamente un peso por activo.")

        self.pesos = validar_pesos(self.pesos, tickers).to_dict()

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

    def _preparar_datos(self):
        """Aplica las mismas restricciones a simulación, informe y gráficos."""
        self._validar_composicion()
        if any(s.frecuencia != "diaria" for s in self.series):
            raise ValueError("La cartera requiere precios de frecuencia diaria para el análisis.")
        monedas = self.obtener_monedas() or {}
        if len(monedas) != len(self.series):
            raise ValueError("Falta la moneda de algún activo; indícala antes de analizar la cartera.")
        if len(set(monedas.values())) != 1:
            raise ValueError("La cartera mezcla monedas; se necesita una moneda común. No se convierten divisas.")
        tabla, diagnostico = alinear_precios(self.obtener_precios())
        validar_tabla(tabla)
        validar_pesos(self.pesos, tabla.columns)
        return tabla, diagnostico

    def monte_carlo(
        self,
        n_sims: int = 10_000,
        horizonte: int = 252,
        retorno=None,
        volatilidad=None,
        nu: float = 5,
        v0: float | None = None,
        semilla: int | None = 42,
        min_observaciones: int = 30,
        activo: str | None = None,
    ) -> SimulationResult:
        """Simula la cartera con Monte Carlo (apartado 4.4).

        Fachada: la cartera solo prepara los datos (limpia y alinea sus precios)
        y delega la matemática en monte_carlo.simular_cartera. Parámetros como en
        simular_cartera: retorno y volatilidad anuales (None = histórico), horizonte
        en días de mercado, v0 = valor inicial de la cartera.
        min_observaciones: fechas comunes mínimas para estimar los parámetros.
        """
        if activo is not None:
            for serie in self.series:
                if serie.ticker == activo:
                    return serie.monte_carlo(n_sims=n_sims, horizonte=horizonte,
                        retorno=retorno, volatilidad=volatilidad, nu=nu, v0=v0,
                        semilla=semilla, min_observaciones=min_observaciones)
            raise ValueError(f"El activo {activo!r} no está en la cartera.")
        tabla, resumen = self._preparar_datos()
        resultado = simular_cartera(
            tabla, self.obtener_pesos(), n_sims=n_sims, horizonte=horizonte,
            retorno=retorno, volatilidad=volatilidad, nu=nu, v0=100.0 if v0 is None else v0,
            semilla=semilla, nombre=self.nombre, min_observaciones=min_observaciones,
        )
        resultado.parametros["limpieza"] = resumen
        return resultado

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
        precios, diagnostico = self._preparar_datos()
        if simulacion is not None:
            usados = simulacion.parametros.get("pesos", {})
            if (simulacion.nombre != self.nombre or set(usados) != set(self.pesos)
                    or any(not isclose(usados[a], p) for a, p in self.pesos.items())):
                raise ValueError("La simulación debe corresponder a esta cartera y a sus pesos actuales.")
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
        precios, _ = self._preparar_datos()
        return generar_plots(
            precios, self.obtener_pesos(), nombre=self.nombre, graficos=graficos,
            benchmark=benchmark, ventana_volatilidad=ventana_volatilidad,
            mostrar=mostrar, carpeta=carpeta,
        )
