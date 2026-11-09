"""Orquesta las llamadas al toolkit para una configuración y reúne los resultados.

No calcula métricas: todas las cifras salen de miax_toolkit (Cartera, reportes,
estimar_parametros, SimulationResult). Aquí se decide qué se llama y sobre qué
fechas, para que el dashboard muestre lo mismo que el informe. No depende de Streamlit.
"""

from dataclasses import dataclass
import re

import pandas as pd

from miax_toolkit import (
    Cartera, SeriePrecios, SimulationResult, alinear_precios, estimar_parametros, limpiar_precios,
)
from miax_toolkit.reportes import contribucion_riesgo, metricas, valor_cartera

from app.configuracion import NU_CASI_NORMAL, Configuracion
from app.universos import NOMBRES

_AVISO = re.compile(r"^- \*\*(ALTO|MEDIO|INFO):\*\* (.+)$")


@dataclass
class Resultados:
    """Salidas del toolkit para una configuración. Se trata como inmutable (está en caché)."""

    config: Configuracion
    series: dict[str, SeriePrecios]
    benchmark: SeriePrecios | None
    cartera: Cartera
    moneda: str
    tabla: pd.DataFrame              # precios alineados de los activos (todas las fechas comunes)
    diagnostico: list[str]           # resumen de limpieza y alineación del toolkit
    tabla_analisis: pd.DataFrame     # fechas comunes también con el benchmark (como el informe)
    referencia: pd.Series | None     # benchmark limpio en esas fechas
    valores: pd.Series               # valor de la cartera, base 100 (reportes.valor_cartera)
    valores_ref: pd.Series | None    # benchmark en base 100
    metricas: dict
    metricas_ref: dict | None
    metricas_activos: dict[str, dict]
    riesgo: pd.Series                # aportación al riesgo (pesos iniciales fijos)
    mu: pd.Series                    # retorno log anual histórico (estimar_parametros)
    sigma: pd.Series
    correlacion: pd.DataFrame        # de rendimientos logarítmicos, la que usa Monte Carlo
    simulacion: SimulationResult
    simulacion_normal: SimulationResult
    informe: str
    advertencias: list[tuple[str, str]]

    @property
    def nombre_ref(self) -> str | None:
        """Nombre legible del benchmark (S&P 500 en lugar de ^GSPC)."""
        return None if self.benchmark is None else NOMBRES.get(self.benchmark.ticker, self.benchmark.ticker)


def extraer_advertencias(informe: str) -> list[tuple[str, str]]:
    """Lee las líneas «- **NIVEL:** texto» de la sección de advertencias del informe.

    El toolkit genera las advertencias en una función privada; se leen del Markdown
    público. Si el formato cambiara, se devuelve una lista vacía y la página muestra
    el Markdown tal cual.
    """
    avisos = []
    if "## Advertencias de riesgo" not in informe:
        return avisos
    seccion = informe.split("## Advertencias de riesgo", 1)[1].split("\n## ", 1)[0]
    for linea in seccion.strip().splitlines():
        coincide = _AVISO.match(linea.strip())
        if coincide:
            avisos.append((coincide.group(1), coincide.group(2)))
    return avisos


def _fechas_comunes(tabla: pd.DataFrame,
                    benchmark: SeriePrecios | None) -> tuple[pd.DataFrame, pd.Series | None]:
    """Restringe el análisis a las fechas con dato del benchmark, igual que hace el informe."""
    if benchmark is None:
        return tabla, None
    referencia, _ = limpiar_precios(benchmark.precios, nombre="benchmark")
    comunes = tabla.index.intersection(referencia.index)
    if len(comunes) < 3:
        raise ValueError("El benchmark necesita al menos 3 fechas válidas comunes con la cartera.")
    return tabla.loc[comunes], referencia.loc[comunes].rename(benchmark.ticker)


def calcular(config: Configuracion, series: dict[str, SeriePrecios],
             benchmark: SeriePrecios | None = None) -> Resultados:
    """Construye la cartera y obtiene del toolkit todo lo que muestran las páginas.

    Los errores de validación del toolkit (ValueError) se propagan sin tocar: la
    interfaz muestra su mensaje tal cual.
    """
    activos = [series[t] for t in config.activos]
    cartera = Cartera(config.nombre, activos, config.pesos_dict)  # valida pesos

    opciones = dict(n_sims=config.n_sims, horizonte=config.horizonte, retorno=config.retorno,
                    volatilidad=config.volatilidad, v0=config.v0, semilla=config.semilla)
    simulacion = cartera.monte_carlo(nu=config.nu, **opciones)  # valida moneda y frecuencia
    simulacion_normal = cartera.monte_carlo(nu=NU_CASI_NORMAL, **opciones)
    informe = cartera.report(
        tasa_libre=config.tasa_libre, nivel_var=config.nivel_var, simulacion=simulacion,
        benchmark=None if benchmark is None else benchmark.precios,
    )

    tabla, diagnostico = alinear_precios(cartera.obtener_precios())
    tabla_analisis, referencia = _fechas_comunes(tabla, benchmark)
    pesos = cartera.obtener_pesos()
    valores = valor_cartera(tabla_analisis, pesos)
    valores_ref = None
    metricas_ref = None
    if referencia is not None:
        valores_ref = valor_cartera(referencia.to_frame(), {referencia.name: 1.0}).rename(referencia.name)
        metricas_ref = metricas(referencia, config.tasa_libre, config.nivel_var)
    mu, sigma, correlacion = estimar_parametros(tabla)

    return Resultados(
        config=config, series=series, benchmark=benchmark, cartera=cartera,
        moneda=next(iter(cartera.obtener_monedas().values())),
        tabla=tabla, diagnostico=diagnostico, tabla_analisis=tabla_analisis, referencia=referencia,
        valores=valores, valores_ref=valores_ref,
        metricas=metricas(valores, config.tasa_libre, config.nivel_var), metricas_ref=metricas_ref,
        metricas_activos={a: metricas(tabla_analisis[a], config.tasa_libre, config.nivel_var)
                          for a in tabla_analisis.columns},
        riesgo=contribucion_riesgo(tabla_analisis, pesos),
        mu=mu, sigma=sigma, correlacion=correlacion,
        simulacion=simulacion, simulacion_normal=simulacion_normal,
        informe=informe, advertencias=extraer_advertencias(informe),
    )
