"""Cuatro fuentes reales, formatos comunes y una cartera. Requiere Internet."""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from miax_toolkit import (
    Cartera, descargar_series, descargar_indicador,
    descargar_sp500_fred, descargar_indicador_fred, descargar_tipo_cambio_bce,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path, default=Path("resultados/fuentes"))
    salida = parser.parse_args().salida
    inicio, fin = "2025-01-01", "2026-01-01"
    yahoo = descargar_series(["AAPL", "MSFT", "^GSPC"], inicio, fin, tipos={"^GSPC": "indice"})
    sp500 = descargar_sp500_fred(inicio, fin)
    desempleo = descargar_indicador_fred("UNRATE", inicio, fin, pais="USA", frecuencia="mensual", unidad="%")
    cambio = descargar_tipo_cambio_bce("USD", "2025-01-01", "2025-02-01")
    pib = descargar_indicador("ESP", "NY.GDP.MKTP.CD", 2020, 2024)

    # Todos los proveedores ofrecen valores, fuente, frecuencia y unidad.
    for serie in [*yahoo.values(), sp500, desempleo, cambio, pib]:
        print(f"{serie.valores.name}: {serie.fuente}, {serie.frecuencia}, {serie.unidad}, {len(serie.valores)} observaciones")
    print("El S&P 500 de Yahoo y FRED usa el mismo objeto:", type(sp500) is type(yahoo["^GSPC"]))
    print("Los indicadores se mantienen separados de los activos de la cartera.")

    cartera = Cartera("Cartera AAPL-MSFT", [yahoo["AAPL"], yahoo["MSFT"]], {"AAPL": .6, "MSFT": .4})
    simulacion = cartera.monte_carlo(n_sims=1000, horizonte=126, semilla=2026)
    salida.mkdir(parents=True, exist_ok=True)
    simulacion.plot(mostrar=False, ruta=salida / "monte_carlo.png")
    cartera.report(benchmark=sp500.valores, simulacion=simulacion, ruta=salida / "informe.md")
    cartera.plots_report(benchmark=sp500.valores, mostrar=False, carpeta=salida)
    plt.close("all")
    print(f"Informe y cinco gráficos guardados en {salida.resolve()}")


if __name__ == "__main__":
    main()
