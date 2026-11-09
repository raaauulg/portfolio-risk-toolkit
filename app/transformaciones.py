"""Series auxiliares para los gráficos que la API pública del toolkit no expone.

Son la excepción a la regla de que el dashboard no calcula métricas. El toolkit las
calcula dentro de sus figuras de matplotlib (reportes._grafico_evolucion y
reportes._grafico_riesgo) sin ofrecerlas como funciones públicas; aquí se replican
con las mismas fórmulas y tests/app/test_transformaciones.py comprueba que coinciden
con esas figuras y con reportes.metricas().
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
