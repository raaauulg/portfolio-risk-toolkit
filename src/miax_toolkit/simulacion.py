"""Motor de simulación de Monte Carlo (apartado 4.4).

Cada activo sigue un movimiento browniano geométrico:

    S(t+1) = S(t) * exp((mu - sigma^2 / 2) * dt + sigma * raiz(dt) * Z)

donde mu es la deriva anual, sigma la volatilidad anual, dt = 1 / dias_por_anio
y Z una normal estándar. En una cartera, los Z de los activos se generan
correlacionados con la matriz de correlación histórica. Con esta definición, el
valor esperado es E[S(T)] = S(0) * exp(mu * T).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from .limpieza import ErrorValidacion, limpiar_serie, validar_pesos
from .metricas import DIAS_POR_ANIO, Rebalanceo, rendimientos_log
from .visual import COLOR_SECUNDARIO, COLOR_TEXTO, COLORES, FONDO, aplicar_estilo, finalizar

if TYPE_CHECKING:
    from matplotlib.figure import Figure

Supuesto = float | Mapping[str, float] | None


@dataclass(frozen=True)
class ParametrosSimulacion:
    """Parámetros de una simulación.

    retorno_anual y volatilidad_anual pueden ser:
      - None: se estiman con el histórico.
      - un número: se aplica a todos los activos.
      - un diccionario {activo: valor}: sustituye solo a esos activos.

    retorno_anual es la deriva mu del modelo. valor_inicial None significa el
    último precio en un activo y 100 en una cartera.
    """

    n_iteraciones: int = 10_000
    horizonte_dias: int = 252
    retorno_anual: Supuesto = None
    volatilidad_anual: Supuesto = None
    valor_inicial: float | None = None
    rebalanceo: Rebalanceo = "diario"
    semilla: int | None = None
    dias_por_anio: int = DIAS_POR_ANIO

    def __post_init__(self) -> None:
        if self.n_iteraciones < 2:
            raise ValueError("n_iteraciones debe ser al menos 2.")
        if self.horizonte_dias < 1:
            raise ValueError("horizonte_dias debe ser al menos 1.")
        if self.dias_por_anio < 1:
            raise ValueError("dias_por_anio debe ser al menos 1.")
        if self.valor_inicial is not None and self.valor_inicial <= 0:
            raise ValueError("valor_inicial debe ser positivo.")
        if self.rebalanceo not in ("diario", "ninguno"):
            raise ValueError("rebalanceo debe ser 'diario' o 'ninguno'.")


@dataclass
class ResultadoSimulacion:
    """Trayectorias simuladas y sus estadísticas.

    trayectorias tiene forma (n_iteraciones, horizonte_dias + 1); la primera
    columna es el valor inicial.
    """

    nombre: str
    trayectorias: np.ndarray
    parametros: ParametrosSimulacion
    supuestos: pd.DataFrame = field(default_factory=pd.DataFrame)

    @property
    def valor_inicial(self) -> float:
        return float(self.trayectorias[0, 0])

    @property
    def valores_finales(self) -> np.ndarray:
        return self.trayectorias[:, -1]

    @property
    def rendimientos_finales(self) -> np.ndarray:
        return self.valores_finales / self.valor_inicial - 1.0

    def percentiles(self, niveles: tuple[float, ...] = (5, 25, 50, 75, 95)) -> pd.DataFrame:
        """Percentiles del valor para cada día del horizonte."""
        return pd.DataFrame(
            np.percentile(self.trayectorias, niveles, axis=0).T,
            columns=[f"p{nivel:g}" for nivel in niveles],
        ).rename_axis("dia")

    def var(self, nivel: float = 0.95) -> float:
        """Pérdida al final del horizonte que solo se supera en (1 - nivel) de casos.

        Se expresa como fracción positiva del valor inicial. Si es negativa, hasta
        ese percentil de escenarios termina con ganancia.
        """
        return float(-np.quantile(self.rendimientos_finales, 1.0 - nivel))

    def cvar(self, nivel: float = 0.95) -> float:
        """Pérdida media de los escenarios que igualan o superan el VaR."""
        rendimientos = self.rendimientos_finales
        corte = np.quantile(rendimientos, 1.0 - nivel)
        return float(-rendimientos[rendimientos <= corte].mean())

    def prob_perdida(self) -> float:
        """Proporción de escenarios que terminan por debajo del valor inicial."""
        return float((self.valores_finales < self.valor_inicial).mean())

    def resumen(self, nivel: float = 0.95) -> dict[str, float]:
        """Estadísticas principales al final del horizonte."""
        finales = self.valores_finales
        return {
            "valor_inicial": self.valor_inicial,
            "valor_medio": float(finales.mean()),
            "valor_mediano": float(np.median(finales)),
            "percentil_5": float(np.percentile(finales, 5)),
            "percentil_95": float(np.percentile(finales, 95)),
            "prob_perdida": self.prob_perdida(),
            "var": self.var(nivel),
            "cvar": self.cvar(nivel),
        }

    def plot(
        self,
        n_trayectorias: int = 40,
        nivel: float = 0.95,
        mostrar: bool = True,
        ruta: str | Path | None = None,
    ) -> "Figure":
        """Muestra las trayectorias y la distribución del valor final."""
        import matplotlib.pyplot as plt

        banda = self.percentiles((0.5, 5, 25, 50, 75, 95, 99.5))
        dias = banda.index.to_numpy()
        color = COLORES[0]

        figura, (eje_tray, eje_dist) = plt.subplots(
            1, 2, figsize=(11, 5.2), sharey=True, width_ratios=[3, 1],
            facecolor=FONDO, layout="constrained",
        )
        n_visibles = min(n_trayectorias, len(self.trayectorias))
        if n_visibles:
            eje_tray.plot(
                dias, self.trayectorias[:n_visibles].T, color=color, alpha=0.12, linewidth=0.7
            )
        eje_tray.fill_between(dias, banda["p5"], banda["p95"], color=color, alpha=0.14,
                              linewidth=0, label="90 % central")
        eje_tray.fill_between(dias, banda["p25"], banda["p75"], color=color, alpha=0.22,
                              linewidth=0, label="50 % central")
        eje_tray.plot(dias, banda["p50"], color=color, linewidth=2, label="Mediana")
        eje_tray.axhline(self.valor_inicial, color=COLOR_SECUNDARIO, linewidth=1,
                         linestyle="--", label="Valor inicial")
        eje_tray.set_xlim(0, dias[-1])
        eje_tray.set_xlabel("Días de mercado")
        eje_tray.set_ylabel("Valor")
        eje_tray.set_title("Trayectorias simuladas", loc="left", color=COLOR_TEXTO, fontsize=11)
        eje_tray.legend(frameon=False, loc="upper left", fontsize=9)

        inferior, superior = float(banda["p0.5"].iloc[-1]), float(banda["p99.5"].iloc[-1])
        inferior = min(inferior, self.valor_inicial)
        margen = (superior - inferior) * 0.05 or abs(superior) * 0.05 or 1.0
        visibles = self.valores_finales[
            (self.valores_finales >= inferior) & (self.valores_finales <= superior)
        ]
        eje_dist.hist(visibles, bins=45, orientation="horizontal", color=color,
                      rwidth=0.85, linewidth=0)
        corte_var = self.valor_inicial * (1.0 - self.var(nivel))
        eje_dist.axhline(corte_var, color=COLORES[1], linewidth=1.5,
                         label=f"VaR {nivel:.0%}: {corte_var:.1f}".replace(".", ",").replace("%", " %"))
        eje_dist.axhline(float(banda["p50"].iloc[-1]), color=COLOR_TEXTO, linewidth=1.2,
                         label=f"Mediana: {banda['p50'].iloc[-1]:.1f}".replace(".", ","))
        eje_dist.set_ylim(inferior - margen, superior + margen)
        eje_dist.set_xlabel("Escenarios")
        eje_dist.set_title("Valor final", loc="left", color=COLOR_TEXTO, fontsize=11)
        eje_dist.legend(frameon=False, loc="upper right", fontsize=8)

        for eje in (eje_tray, eje_dist):
            aplicar_estilo(eje)
        figura.suptitle(
            f"Monte Carlo: {self.nombre} ("
            + f"{len(self.trayectorias):,}".replace(",", ".")
            + f" escenarios, {self.parametros.horizonte_dias} días)",
            x=0.01, ha="left", color=COLOR_TEXTO, fontsize=13, fontweight="bold",
        )
        return finalizar(figura, mostrar=mostrar, ruta=ruta)


def _resolver_supuesto(
    valor: Supuesto, historico: pd.Series, etiqueta: str, minimo: float | None = None
) -> pd.Series:
    """Combina los supuestos del usuario con la estimación histórica."""
    resultado = historico.copy()
    if isinstance(valor, Mapping):
        desconocidos = sorted(set(valor) - set(resultado.index))
        if desconocidos:
            raise ErrorValidacion(f"{etiqueta}: activos desconocidos {desconocidos}.")
        for activo, dato in valor.items():
            resultado[activo] = float(dato)
    elif valor is not None:
        resultado.loc[:] = float(valor)
    if not np.isfinite(resultado.to_numpy()).all():
        raise ErrorValidacion(f"{etiqueta}: contiene valores no finitos.")
    if minimo is not None and (resultado < minimo).any():
        raise ErrorValidacion(f"{etiqueta}: no puede ser menor que {minimo}.")
    return resultado


def _factor_correlacion(correlacion: np.ndarray) -> np.ndarray:
    """Devuelve L tal que L @ L.T reproduce la correlación.

    Usa autovalores en lugar de Cholesky porque Cholesky falla si dos activos
    están perfectamente correlacionados o hay más activos que datos.
    """
    autovalores, autovectores = np.linalg.eigh(correlacion)
    return autovectores * np.sqrt(np.clip(autovalores, 0.0, None))


def simular_cartera(
    precios: pd.DataFrame,
    pesos: pd.Series | Mapping[str, float],
    parametros: ParametrosSimulacion | None = None,
    nombre: str = "Cartera",
) -> ResultadoSimulacion:
    """Simula una cartera con activos correlacionados.

    precios deben estar ya limpios y alineados (ver limpieza.alinear_precios).
    """
    parametros = parametros or ParametrosSimulacion()
    pesos_serie = validar_pesos(pesos, precios.columns)
    rendimientos = rendimientos_log(precios)
    dias_anio = parametros.dias_por_anio

    # Con mu = media_log * dias + sigma^2 / 2, la deriva diaria del modelo
    # coincide con la media histórica de los rendimientos logarítmicos.
    sigma_hist = rendimientos.std(ddof=1) * np.sqrt(dias_anio)
    mu_hist = rendimientos.mean() * dias_anio + sigma_hist**2 / 2.0
    sigma = _resolver_supuesto(parametros.volatilidad_anual, sigma_hist,
                               "volatilidad_anual", minimo=0.0)
    mu = _resolver_supuesto(parametros.retorno_anual, mu_hist, "retorno_anual")

    correlacion = rendimientos.corr().fillna(0.0).to_numpy(copy=True)
    np.fill_diagonal(correlacion, 1.0)
    factor = _factor_correlacion(correlacion)

    dt = 1.0 / dias_anio
    deriva = (mu.to_numpy() - sigma.to_numpy() ** 2 / 2.0) * dt
    difusion = sigma.to_numpy() * np.sqrt(dt)
    w = pesos_serie.to_numpy()

    n, h = parametros.n_iteraciones, parametros.horizonte_dias
    valor_0 = parametros.valor_inicial if parametros.valor_inicial is not None else 100.0
    generador = np.random.default_rng(parametros.semilla)

    # Se avanza día a día para no guardar en memoria cada activo de cada escenario.
    trayectorias = np.empty((n, h + 1))
    trayectorias[:, 0] = valor_0
    participaciones = np.tile(w, (n, 1))  # solo se usa sin rebalanceo
    for dia in range(1, h + 1):
        z = generador.standard_normal((n, len(w))) @ factor.T
        factor_dia = np.exp(deriva + difusion * z)
        if parametros.rebalanceo == "diario":
            trayectorias[:, dia] = trayectorias[:, dia - 1] * (factor_dia @ w)
        else:
            participaciones = participaciones * factor_dia
            trayectorias[:, dia] = valor_0 * participaciones.sum(axis=1)

    supuestos = pd.DataFrame({"peso": pesos_serie, "retorno_anual": mu,
                              "volatilidad_anual": sigma})
    return ResultadoSimulacion(nombre, trayectorias, parametros, supuestos)


def simular_activo(
    precios: pd.Series,
    parametros: ParametrosSimulacion | None = None,
    nombre: str | None = None,
) -> ResultadoSimulacion:
    """Simula un solo activo. Por defecto parte de su último precio."""
    parametros = parametros or ParametrosSimulacion()
    etiqueta = nombre or str(precios.name or "Activo")
    limpia, _ = limpiar_serie(precios, nombre=etiqueta)
    tabla = limpia.to_frame(etiqueta)
    if parametros.valor_inicial is None:
        parametros = replace(parametros, valor_inicial=float(limpia.iloc[-1]))
    return simular_cartera(tabla, {etiqueta: 1.0}, parametros, nombre=etiqueta)
