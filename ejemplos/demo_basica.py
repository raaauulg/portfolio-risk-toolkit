"""Demostración del modelado del apartado 4.3 sin conexión a Internet."""

import pandas as pd

from miax_toolkit import Cartera, SeriePrecios


def main() -> None:
    fechas = pd.bdate_range("2025-01-02", periods=60)
    activo_a = SeriePrecios(
        ticker="AAA",
        precios=pd.Series([100 + 0.3 * i for i in range(60)], index=fechas),
        fuente="datos sinteticos",
        moneda="EUR",
    )
    activo_b = SeriePrecios(
        ticker="BBB",
        precios=pd.Series([80 + 0.2 * i for i in range(60)], index=fechas),
        fuente="datos sinteticos",
        moneda="EUR",
    )
    cartera = Cartera(
        "Ejemplo del taller", [activo_a, activo_b],
        {"AAA": 0.6, "BBB": 0.4}
    )

    print("Serie:", activo_a.ticker)
    print("Media:", round(activo_a.media, 2))
    print("Desviacion tipica muestral:", round(activo_a.desviacion_tipica, 2))
    print("Ponderaciones:", cartera.obtener_pesos())
    print("Numero de activos:", len(cartera.obtener_precios()))


if __name__ == "__main__":
    main()
