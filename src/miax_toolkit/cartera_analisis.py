"""Conecta la simulación y los reportes con la clase Cartera.

CarteraAnalisisMixin añade a la Cartera los métodos monte_carlo(), report() y
plots_report(). Un mixin es una clase pensada para heredar métodos de ella.
La Cartera solo tiene que implementar dos métodos:

    @dataclass
    class Cartera(CarteraAnalisisMixin):
        ...
        def obtener_precios(self):  # {activo: Series} o DataFrame de precios
            ...
        def obtener_pesos(self):    # {activo: peso}, deben sumar 1
            ...

Así, el cálculo no depende de cómo guarde la Cartera sus datos, y tampoco de la
API de la que procedan: esa es la separación por capas que pide el enunciado.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import pandas as pd

from .limpieza import ErrorValidacion, ResultadoLimpieza, alinear_precios, validar_pesos
from .metricas import Rebalanceo
from .reportes import GRAFICOS, SECCIONES, UmbralesRiesgo, generar_plots, generar_report
from .simulacion import (
    ParametrosSimulacion,
    ResultadoSimulacion,
    Supuesto,
    simular_activo,
    simular_cartera,
)

if TYPE_CHECKING:
    from matplotlib.figure import Figure


class CarteraAnalisisMixin:
    """Métodos de análisis que hereda la Cartera."""

    def obtener_precios(self) -> pd.DataFrame | Mapping[str, pd.Series]:
        raise NotImplementedError("La Cartera debe implementar obtener_precios().")

    def obtener_pesos(self) -> pd.Series | Mapping[str, float]:
        raise NotImplementedError("La Cartera debe implementar obtener_pesos().")

    def obtener_monedas(self) -> Mapping[str, str] | None:
        """Opcional: {activo: moneda}, para avisar si la cartera mezcla monedas."""
        return None

    def _nombre_cartera(self) -> str:
        return str(getattr(self, "nombre", "Cartera"))

    def preparar_datos(
        self, metodo_alineacion: Literal["interseccion", "union"] = "interseccion"
    ) -> tuple[ResultadoLimpieza, pd.Series]:
        """Limpia y alinea los precios y comprueba los pesos."""
        limpieza = alinear_precios(self.obtener_precios(), metodo=metodo_alineacion)
        pesos = validar_pesos(self.obtener_pesos(), limpieza.precios.columns)
        return limpieza, pesos

    def monte_carlo(
        self,
        n_iteraciones: int = 10_000,
        horizonte_dias: int = 252,
        retorno_anual: Supuesto = None,
        volatilidad_anual: Supuesto = None,
        valor_inicial: float | None = None,
        rebalanceo: Rebalanceo = "diario",
        semilla: int | None = None,
        activo: str | None = None,
        metodo_alineacion: Literal["interseccion", "union"] = "interseccion",
    ) -> ResultadoSimulacion:
        """Simula la cartera completa, o un solo activo si se indica activo.

        El resultado se dibuja con resultado.plot().
        """
        parametros = ParametrosSimulacion(
            n_iteraciones=n_iteraciones,
            horizonte_dias=horizonte_dias,
            retorno_anual=retorno_anual,
            volatilidad_anual=volatilidad_anual,
            valor_inicial=valor_inicial,
            rebalanceo=rebalanceo,
            semilla=semilla,
        )
        if activo is not None:
            precios = self.obtener_precios()
            if activo not in precios:
                raise ErrorValidacion(f"El activo {activo!r} no está en la cartera.")
            return simular_activo(precios[activo], parametros, nombre=activo)
        limpieza, pesos = self.preparar_datos(metodo_alineacion)
        return simular_cartera(limpieza.precios, pesos, parametros, self._nombre_cartera())

    def report(
        self,
        tasa_libre: float = 0.0,
        nivel_var: float = 0.95,
        rebalanceo: Rebalanceo = "diario",
        benchmark: pd.Series | None = None,
        simulacion: ResultadoSimulacion | None = None,
        secciones: Sequence[str] = SECCIONES,
        umbrales: UmbralesRiesgo | None = None,
        metodo_alineacion: Literal["interseccion", "union"] = "interseccion",
        ruta: str | Path | None = None,
    ) -> str:
        """Devuelve un informe en Markdown con métricas, diagnóstico y advertencias."""
        limpieza, pesos = self.preparar_datos(metodo_alineacion)
        return generar_report(
            limpieza.precios,
            pesos,
            nombre=self._nombre_cartera(),
            tasa_libre=tasa_libre,
            nivel_var=nivel_var,
            rebalanceo=rebalanceo,
            benchmark=benchmark,
            simulacion=simulacion,
            secciones=secciones,
            umbrales=umbrales,
            incidencias=limpieza.incidencias,
            monedas=self.obtener_monedas(),
            ruta=ruta,
        )

    def plots_report(
        self,
        graficos: Sequence[str] = GRAFICOS,
        rebalanceo: Rebalanceo = "diario",
        benchmark: pd.Series | None = None,
        ventana_volatilidad: int = 63,
        metodo_alineacion: Literal["interseccion", "union"] = "interseccion",
        mostrar: bool = True,
        carpeta: str | Path | None = None,
    ) -> dict[str, "Figure"]:
        """Crea los gráficos de análisis de la cartera."""
        limpieza, pesos = self.preparar_datos(metodo_alineacion)
        return generar_plots(
            limpieza.precios,
            pesos,
            nombre=self._nombre_cartera(),
            rebalanceo=rebalanceo,
            benchmark=benchmark,
            graficos=graficos,
            ventana_volatilidad=ventana_volatilidad,
            mostrar=mostrar,
            carpeta=carpeta,
        )
