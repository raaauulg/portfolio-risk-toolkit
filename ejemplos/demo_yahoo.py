"""Mismo flujo que demo_sintetica.py, con precios reales de Yahoo Finance.

Necesita internet. CarteraYahoo solo sirve para probar: en el proyecto se sustituye
por la Cartera real y el extractor del grupo.

    python ejemplos/demo_yahoo.py
"""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yfinance as yf

from miax_toolkit.cartera_analisis import CarteraAnalisisMixin

SALIDA = Path(__file__).parent / "salida_yahoo"
PESOS = {"AAPL": 0.3, "MSFT": 0.3, "JPM": 0.2, "XOM": 0.2}


@dataclass
class CarteraYahoo(CarteraAnalisisMixin):
    nombre: str
    precios: pd.DataFrame
    pesos: dict[str, float]

    def obtener_precios(self) -> pd.DataFrame:
        return self.precios

    def obtener_pesos(self) -> dict[str, float]:
        return self.pesos


def main() -> None:
    tickers = [*PESOS, "^GSPC"]
    cierres = yf.download(tickers, period="5y", auto_adjust=True, progress=False)["Close"]
    indice = cierres["^GSPC"].rename("S&P 500")

    cartera = CarteraYahoo("Cartera EEUU", cierres[list(PESOS)], PESOS)
    simulacion = cartera.monte_carlo(semilla=42)
    simulacion.plot(mostrar=False, ruta=SALIDA / "monte_carlo.png")
    print(cartera.report(tasa_libre=0.03, benchmark=indice, simulacion=simulacion,
                         ruta=SALIDA / "informe.md"))
    cartera.plots_report(mostrar=False, carpeta=SALIDA, benchmark=indice)


if __name__ == "__main__":
    main()
