"""Demostración de extracción y modelado. Requiere conexión a Internet."""

from miax_toolkit import (
    Cartera,
    SerieIndicador,
    SeriePrecios,
    descargar_indicador,
    descargar_series,
)


def mostrar_serie(serie: SeriePrecios | SerieIndicador) -> None:
    """Consulta cualquier fuente mediante los mismos tres atributos."""
    valores = serie.valores
    print(
        f"{valores.name}: {serie.fuente}, frecuencia {serie.frecuencia}, "
        f"{len(valores)} observaciones, "
        f"desde {valores.index.min().date()} hasta {valores.index.max().date()}"
    )


def main() -> None:
    datos = descargar_series(
        ["AAPL", "MSFT", "^GSPC"],
        "2025-01-01", "2026-01-01",
        tipos={"^GSPC": "indice"},
    )
    pib = descargar_indicador("ESP", "NY.GDP.MKTP.CD", 2020, 2024)

    print("DATOS DE LAS DOS FUENTES (interfaz común)")
    for serie in [*datos.values(), pib]:
        mostrar_serie(serie)

    print("\nESTADÍSTICOS AUTOMÁTICOS DE LOS PRECIOS")
    for serie in datos.values():
        print(
            f"{serie.ticker} ({serie.tipo_activo}, {serie.moneda}): "
            f"media={serie.media:.2f}, desviación típica={serie.desviacion_tipica:.2f}"
        )
    print("La desviación típica se calcula sobre precios, no sobre rentabilidades.")

    # El índice se consulta como referencia; el PIB se conserva por separado.
    cartera = Cartera(
        "Ejemplo académico", [datos["AAPL"], datos["MSFT"]],
        {"AAPL": 0.6, "MSFT": 0.4},
    )
    print("\nCARTERA DE DOS ACCIONES")
    print("Pesos:", cartera.obtener_pesos())
    print("Suma de los pesos:", sum(cartera.obtener_pesos().values()))
    print("Monedas:", cartera.obtener_monedas())
    print("Activos:", list(cartera.obtener_precios()))

    print("\nPIB NOMINAL DE ESPAÑA (USD corrientes, años inclusivos)")
    print(pib.valores.to_string())


if __name__ == "__main__":
    main()
