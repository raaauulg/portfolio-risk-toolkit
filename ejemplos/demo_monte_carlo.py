"""Demostración del Monte Carlo (apartado 4.4) sin conexión a Internet.

Genera precios sintéticos de tres activos correlacionados (semilla fija),
simula la cartera y uno de sus activos, imprime la interpretación y guarda
el gráfico en docs/img/monte_carlo_cartera.png.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # guarda el PNG sin abrir ventanas ni bloquear

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from miax_toolkit import Cartera, SeriePrecios

SEMILLA = 2026
RUTA_GRAFICO = Path(__file__).resolve().parents[1] / "docs" / "img" / "monte_carlo_cartera.png"


def precios_sinteticos(n_dias: int = 500) -> pd.DataFrame:
    """Tres activos con rendimientos log diarios normales correlacionados."""
    rng = np.random.default_rng(SEMILLA)
    fechas = pd.bdate_range("2024-01-02", periods=n_dias)
    mu_anual = np.array([0.08, 0.05, 0.03])
    vol_anual = np.array([0.25, 0.18, 0.10])
    correlacion = np.array([[1.0, 0.6, 0.2], [0.6, 1.0, 0.3], [0.2, 0.3, 1.0]])

    covarianza_diaria = np.outer(vol_anual, vol_anual) * correlacion / 252
    rendimientos = rng.multivariate_normal(mu_anual / 252, covarianza_diaria, size=n_dias)
    precios = 100 * np.exp(np.cumsum(rendimientos, axis=0))
    return pd.DataFrame(precios, index=fechas, columns=["ACC_A", "ACC_B", "BONO_C"])


def main() -> None:
    tabla = precios_sinteticos()
    series = [
        SeriePrecios(ticker, tabla[ticker], fuente="datos sinteticos", moneda="EUR")
        for ticker in tabla.columns
    ]
    cartera = Cartera("Cartera demo", series, {"ACC_A": 0.5, "ACC_B": 0.3, "BONO_C": 0.2})

    # Cartera: parámetros históricos, 1 año (252 días de mercado), 10 000 escenarios.
    resultado = cartera.monte_carlo(n_sims=10_000, horizonte=252, v0=10_000.0, semilla=SEMILLA)
    print(resultado.interpretacion())
    print("Diagnóstico de limpieza:", *resultado.parametros["limpieza"], sep="\n- ")

    # Un activo con supuestos propios: 6 % de retorno y 30 % de volatilidad anuales.
    activo = series[0].monte_carlo(
        n_sims=5_000, horizonte=126, retorno=0.06, volatilidad=0.30, semilla=SEMILLA
    )
    print()
    print(activo.interpretacion())

    RUTA_GRAFICO.parent.mkdir(parents=True, exist_ok=True)
    figura = resultado.plot(mostrar=False, ruta=RUTA_GRAFICO)
    plt.close(figura)
    print(f"\nGráfico guardado en {RUTA_GRAFICO}")


if __name__ == "__main__":
    main()
