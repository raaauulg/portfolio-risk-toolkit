"""Ejemplo reproducible de Monte Carlo, report() y plots_report().

Usa precios inventados con semilla fija, así que funciona sin internet. La clase
CarteraDemo solo sirve para este ejemplo; en el proyecto se usa la Cartera real.

Ejecutar desde la carpeta principal del proyecto:
    python ejemplos/demo_sintetica.py
"""

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # guarda los gráficos en archivos sin abrir ventanas

import numpy as np
import pandas as pd

from miax_toolkit.cartera_analisis import CarteraAnalisisMixin

SALIDA = Path(__file__).parent / "salida"


def crear_precios(n: int = 1000, semilla: int = 42) -> dict[str, pd.Series]:
    """Crea cuatro activos correlacionados con calendarios e incidencias distintos."""
    generador = np.random.default_rng(semilla)
    fechas = pd.bdate_range("2022-01-03", periods=n)
    nombres = ["TEC", "BANCO", "ENERGIA", "BONOS"]
    medias = np.array([0.12, 0.08, 0.06, 0.03]) / 252
    volatilidades = np.array([0.32, 0.26, 0.24, 0.06]) / np.sqrt(252)
    correlacion = np.array([[1.00, 0.55, 0.30, -0.10],
                            [0.55, 1.00, 0.40, -0.05],
                            [0.30, 0.40, 1.00, 0.00],
                            [-0.10, -0.05, 0.00, 1.00]])
    covarianza = np.outer(volatilidades, volatilidades) * correlacion
    rendimientos = generador.multivariate_normal(medias, covarianza, n)
    tabla = pd.DataFrame(100 * np.exp(rendimientos.cumsum(axis=0)), index=fechas, columns=nombres)

    series = {nombre: tabla[nombre].copy() for nombre in nombres}
    series["BANCO"] = series["BANCO"].drop(fechas[generador.choice(n, 12, replace=False)])  # festivos
    series["ENERGIA"].iloc[[200, 201, 500]] = np.nan  # datos ausentes
    series["TEC"].iloc[300] = -1.0  # error del proveedor
    return series


def crear_indice(n: int = 1000, semilla: int = 7) -> pd.Series:
    """Crea un índice de referencia inventado, correlacionado con TEC y BANCO."""
    precios = crear_precios(n)
    media = np.log(pd.concat([precios["TEC"].where(precios["TEC"] > 0),
                              precios["BANCO"]], axis=1).ffill()).mean(axis=1)
    ruido = np.random.default_rng(semilla).normal(0, 0.004, n).cumsum()
    return np.exp(media + ruido).rename("Índice")


@dataclass
class CarteraDemo(CarteraAnalisisMixin):
    nombre: str
    precios: dict[str, pd.Series]
    pesos: dict[str, float]

    def obtener_precios(self) -> dict[str, pd.Series]:
        return self.precios

    def obtener_pesos(self) -> dict[str, float]:
        return self.pesos


def main() -> None:
    cartera = CarteraDemo(
        nombre="Cartera demo",
        precios=crear_precios(),
        pesos={"TEC": 0.45, "BANCO": 0.25, "ENERGIA": 0.20, "BONOS": 0.10},
    )

    simulacion = cartera.monte_carlo(n_iteraciones=10_000, horizonte_dias=252, semilla=42)
    simulacion.plot(mostrar=False, ruta=SALIDA / "monte_carlo.png")

    prudente = cartera.monte_carlo(retorno_anual=0.04, volatilidad_anual=0.25, semilla=42)
    print(f"Prob. de pérdida con retorno histórico: {simulacion.prob_perdida():.1%}")
    print(f"Prob. de pérdida con supuesto prudente: {prudente.prob_perdida():.1%}")

    informe = cartera.report(tasa_libre=0.02, simulacion=simulacion, benchmark=crear_indice(),
                             ruta=SALIDA / "informe.md")
    print(informe)

    cartera.plots_report(mostrar=False, carpeta=SALIDA, benchmark=crear_indice())
    print(f"Archivos guardados en {SALIDA}")


if __name__ == "__main__":
    main()
