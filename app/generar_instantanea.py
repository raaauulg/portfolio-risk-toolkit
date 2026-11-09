"""Genera la instantánea sin conexión de data/sample/ con las funciones del toolkit.

Uso (requiere Internet, solo para regenerarla):
    python -m app.generar_instantanea

Escribe un CSV largo por universo (fecha, ticker, cierre), que conserva el
calendario propio de cada serie, y series.csv con los metadatos de cada una.
"""

import argparse
from datetime import date
from pathlib import Path

import pandas as pd

from miax_toolkit import SeriePrecios, descargar_series, descargar_sp500_fred

from app.universos import FIN, INICIO, NOMBRES, UNIVERSOS

CARPETA = Path(__file__).resolve().parents[1] / "data" / "sample"


def descargar_universo(clave: str) -> list[SeriePrecios]:
    """Descarga acciones e índices de un universo y comprueba su moneda."""
    universo = UNIVERSOS[clave]
    series = list(descargar_series(list(universo.acciones), INICIO, FIN).values())
    if universo.indices_yahoo:
        tipos = {indice: "indice" for indice in universo.indices_yahoo}
        series += descargar_series(list(universo.indices_yahoo), INICIO, FIN, tipos=tipos).values()
    if universo.sp500_fred:
        series.append(descargar_sp500_fred(INICIO, FIN))
    distintas = {s.ticker: s.moneda for s in series if s.moneda != universo.moneda}
    if distintas:
        raise ValueError(f"Monedas inesperadas en {clave}: {distintas}")
    return series


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path, default=CARPETA)
    salida = parser.parse_args().salida
    salida.mkdir(parents=True, exist_ok=True)
    hoy = date.today().isoformat()

    metadatos = []
    for clave in UNIVERSOS:
        series = descargar_universo(clave)
        filas = [
            pd.DataFrame({"fecha": s.precios.index.strftime("%Y-%m-%d"), "ticker": s.ticker,
                          "cierre": s.precios.to_numpy()})
            for s in series
        ]
        pd.concat(filas).to_csv(salida / f"precios_{clave}.csv", index=False, float_format="%.6f")
        metadatos += [{
            "ticker": s.ticker, "nombre": NOMBRES.get(s.ticker, s.ticker), "universo": clave,
            "fuente": s.fuente, "tipo_activo": s.tipo_activo, "moneda": s.moneda,
            "frecuencia": s.frecuencia, "unidad": s.unidad, "ajuste": s.ajuste,
            "inicio": INICIO, "fin_exclusivo": FIN, "fecha_descarga": hoy,
        } for s in series]
        print(f"{clave}: {len(series)} series, {sum(len(f) for f in filas)} observaciones")
    pd.DataFrame(metadatos).to_csv(salida / "series.csv", index=False)
    print(f"Instantánea guardada en {salida}")


if __name__ == "__main__":
    main()
