"""Transformaciones de presentación que la API pública del toolkit no expone.

Es la ÚNICA excepción a la regla «el dashboard no calcula métricas». El toolkit
calcula estas series dentro de sus figuras de matplotlib (reportes._grafico_evolucion
y reportes._grafico_riesgo), pero no las ofrece como funciones públicas. Aquí se
replican con las mismas fórmulas, y tests/app/test_transformaciones.py comprueba
que coinciden con los datos de esas figuras y con reportes.metricas().

Se mantienen aquí porque su uso es visual y la API pública del núcleo no las expone.
"""

import numpy as np
import pandas as pd

from miax_toolkit.reportes import DIAS_POR_ANIO


def caidas(valores: pd.Series) -> pd.Series:
    """Caída desde el máximo previo (drawdown), en tanto por uno (-0,25 = -25 %)."""
    return valores / valores.cummax() - 1


def volatilidad_movil(valores: pd.Series, ventana: int) -> pd.Series:
    """Volatilidad anualizada de los rendimientos simples en una ventana móvil, en tanto por uno."""
    return valores.pct_change().rolling(ventana).std() * np.sqrt(DIAS_POR_ANIO)


def rendimientos(valores: pd.Series) -> pd.Series:
    """Rendimientos simples diarios, los mismos sobre los que metricas() calcula VaR y CVaR."""
    return valores.pct_change(fill_method=None).dropna()
