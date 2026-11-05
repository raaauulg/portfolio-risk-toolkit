"""Cálculos financieros compartidos por la simulación y los reportes."""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd

DIAS_POR_ANIO = 252
Rebalanceo = Literal["diario", "ninguno"]


def rendimientos_simples(precios: pd.DataFrame | pd.Series) -> pd.DataFrame | pd.Series:
    """Rendimiento diario: P(t) / P(t-1) - 1."""
    return precios.pct_change().dropna(how="all")


def rendimientos_log(precios: pd.DataFrame | pd.Series) -> pd.DataFrame | pd.Series:
    """Rendimiento logarítmico diario: ln(P(t) / P(t-1))."""
    return np.log(precios).diff().dropna(how="all")


def valor_cartera(
    precios: pd.DataFrame,
    pesos: pd.Series,
    rebalanceo: Rebalanceo = "diario",
    base: float = 100.0,
) -> pd.Series:
    """Evolución histórica del valor de la cartera, empezando en base.

    "diario" vuelve a los pesos objetivo cada día; "ninguno" compra al inicio y
    deja que los pesos cambien con los precios. No incluye costes de transacción.
    """
    pesos = pesos.reindex(precios.columns)
    if rebalanceo == "diario":
        rendimiento = rendimientos_simples(precios).fillna(0.0) @ pesos
        valores = base * (1.0 + rendimiento).cumprod()
        inicio = pd.Series([base], index=precios.index[:1])
        serie = pd.concat([inicio, valores])
    elif rebalanceo == "ninguno":
        serie = base * (precios / precios.iloc[0] @ pesos)
    else:
        raise ValueError("rebalanceo debe ser 'diario' o 'ninguno'.")
    serie.name = "Cartera"
    return serie


def retorno_anualizado(valores: pd.Series, dias_por_anio: int = DIAS_POR_ANIO) -> float:
    """Crecimiento compuesto anual: (V_final / V_inicial) ^ (dias_anio / n) - 1."""
    periodos = len(valores) - 1
    if periodos < 1 or valores.iloc[0] <= 0 or valores.iloc[-1] <= 0:
        return float("nan")
    return float((valores.iloc[-1] / valores.iloc[0]) ** (dias_por_anio / periodos) - 1)


def volatilidad_anualizada(
    rendimientos: pd.Series, dias_por_anio: int = DIAS_POR_ANIO
) -> float:
    """Desviación típica diaria * raíz(días por año)."""
    return float(rendimientos.std(ddof=1) * np.sqrt(dias_por_anio))


def ratio_sharpe(
    rendimientos: pd.Series, tasa_libre: float = 0.0, dias_por_anio: int = DIAS_POR_ANIO
) -> float:
    """(rendimiento medio anual - tasa libre) / volatilidad anual."""
    volatilidad = volatilidad_anualizada(rendimientos, dias_por_anio)
    if volatilidad == 0:
        return float("nan")
    return float((rendimientos.mean() * dias_por_anio - tasa_libre) / volatilidad)


def ratio_sortino(
    rendimientos: pd.Series, tasa_libre: float = 0.0, dias_por_anio: int = DIAS_POR_ANIO
) -> float:
    """Como el Sharpe, pero solo penaliza los días por debajo de la tasa libre."""
    exceso = rendimientos - tasa_libre / dias_por_anio
    riesgo_bajista = np.sqrt((exceso.clip(upper=0.0) ** 2).mean()) * np.sqrt(dias_por_anio)
    if riesgo_bajista == 0:
        return float("nan")
    return float(exceso.mean() * dias_por_anio / riesgo_bajista)


def caidas(valores: pd.Series) -> pd.Series:
    """Caída frente al máximo anterior en cada fecha (0 = en máximos)."""
    return valores / valores.cummax() - 1.0


def var_historico(rendimientos: pd.Series, nivel: float = 0.95) -> float:
    """Pérdida diaria que solo se supera en (1 - nivel) de los días (positiva)."""
    return float(-np.quantile(rendimientos, 1.0 - nivel))


def cvar_historico(rendimientos: pd.Series, nivel: float = 0.95) -> float:
    """Pérdida media de los días que igualan o superan el VaR (positiva)."""
    corte = np.quantile(rendimientos, 1.0 - nivel)
    return float(-rendimientos[rendimientos <= corte].mean())


def contribucion_riesgo(rendimientos: pd.DataFrame, pesos: pd.Series) -> pd.Series:
    """Parte de la varianza de la cartera que aporta cada activo (suma 1)."""
    pesos = pesos.reindex(rendimientos.columns)
    covarianza = rendimientos.cov()
    aportaciones = pesos * (covarianza @ pesos)
    total = float(aportaciones.sum())
    if total == 0:
        return aportaciones * 0.0
    return aportaciones / total


def concentracion_efectiva(pesos: pd.Series) -> float:
    """Número efectivo de activos: 1 / suma(peso^2)."""
    return float(1.0 / (pesos**2).sum())
