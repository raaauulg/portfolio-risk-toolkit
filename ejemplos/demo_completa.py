"""Ejemplo reproducible sin Internet: modelado, limpieza, simulación e informes.

Todos los precios son sintéticos y se identifican como tales.
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from miax_toolkit import Cartera, SeriePrecios


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path, default=Path("resultados/demo"))
    salida = parser.parse_args().salida
    salida.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(2026)
    fechas = pd.bdate_range("2024-01-02", periods=504)
    cov = np.array([[.0004, .00012, .00002], [.00012, .000225, .00001], [.00002, .00001, .000025]])
    rendimientos = rng.multivariate_normal([.0003, .0002, .0001], cov, len(fechas))
    tabla = pd.DataFrame(100*np.exp(rendimientos.cumsum(axis=0)), index=fechas, columns=["ACC_A", "ACC_B", "BONO_C"])
    tabla.loc[fechas[5], "ACC_B"] = np.nan  # observación ausente para mostrar la limpieza
    series = [SeriePrecios(a, tabla[a], "sintetica", moneda="EUR") for a in tabla]
    cartera = Cartera("Cartera sintética", series, {"ACC_A": .5, "ACC_B": .3, "BONO_C": .2})
    for serie in series:
        print(f"{serie.ticker}: media de precios={serie.media:.2f}, desviación de precios={serie.desviacion_tipica:.2f}")

    simulacion = cartera.monte_carlo(n_sims=2000, horizonte=252, retorno=.06, semilla=2026)
    print(simulacion.interpretacion())
    individual = series[0].monte_carlo(n_sims=500, horizonte=126, retorno=.06, volatilidad=.25)
    print(individual.interpretacion())
    simulacion.plot(mostrar=False, ruta=salida / "monte_carlo.png")
    print(cartera.report(simulacion=simulacion, tasa_libre=.02, ruta=salida / "informe.md"))
    cartera.plots_report(mostrar=False, carpeta=salida)
    plt.close("all")
    print(f"Informe y cinco gráficos guardados en {salida.resolve()}")


if __name__ == "__main__":
    main()
