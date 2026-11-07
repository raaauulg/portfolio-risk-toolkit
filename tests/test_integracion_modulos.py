"""Pruebas de integraciÃ³n entre los mÃ³dulos de Javi (modelos, cartera) y de
Amalia (limpieza, monte_carlo). Datos sintÃ©ticos, semilla fija y sin Internet.

La mediana del motor y Cartera.monte_carlo() se prueban en la Fase 2.
"""

import matplotlib

matplotlib.use("Agg")  # backend sin ventana: los tests no abren grÃ¡ficos

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

import miax_toolkit
from miax_toolkit import (
    Cartera,
    SeriePrecios,
    SimulationResult,
    alinear_precios,
    simular_cartera,
)

SEMILLA = 123

API_PUBLICA = [
    "descargar_serie", "descargar_series", "descargar_indicador",
    "SeriePrecios", "SerieIndicador", "Cartera",
    "limpiar_precios", "alinear_precios", "validar_pesos",
    "estimar_parametros", "simular_cartera", "simular_activo", "SimulationResult",
]


def _precios_sinteticos(fechas: pd.DatetimeIndex, semilla: int, nombre: str) -> pd.Series:
    """Paseo aleatorio geomÃ©trico: rendimientos log diarios ~ N(0.0003, 0.01)."""
    rng = np.random.default_rng(semilla)
    rendimientos = rng.normal(0.0003, 0.01, len(fechas))
    return pd.Series(100 * np.exp(np.cumsum(rendimientos)), index=fechas, name=nombre)


@pytest.fixture
def precios_dos_calendarios() -> dict[str, pd.Series]:
    """Dos activos con calendarios distintos: uno cotiza todos los dÃ­as hÃ¡biles,
    el otro no cotiza los lunes (simula festivos de otra bolsa)."""
    habiles = pd.bdate_range("2024-01-01", periods=120)
    sin_lunes = habiles[habiles.day_of_week != 0]
    return {
        "AAA": _precios_sinteticos(habiles, SEMILLA, "AAA"),
        "BBB": _precios_sinteticos(sin_lunes, SEMILLA + 1, "BBB"),
    }


def test_api_publica_importable_desde_el_paquete():
    for nombre in API_PUBLICA:
        assert hasattr(miax_toolkit, nombre), nombre
    assert set(API_PUBLICA) <= set(miax_toolkit.__all__)


def test_alinear_precios_conserva_solo_fechas_comunes(precios_dos_calendarios):
    tabla, resumen = alinear_precios(precios_dos_calendarios)

    comunes = precios_dos_calendarios["AAA"].index.intersection(
        precios_dos_calendarios["BBB"].index
    )
    assert list(tabla.columns) == ["AAA", "BBB"]
    assert tabla.index.equals(comunes)
    assert not tabla.isna().any().any()
    assert resumen  # al menos el recuento de observaciones y la alineaciÃ³n


def test_simular_cartera_forma_valor_inicial_y_semilla(precios_dos_calendarios):
    tabla, _ = alinear_precios(precios_dos_calendarios)
    pesos = {"AAA": 0.6, "BBB": 0.4}
    opciones = dict(n_sims=200, horizonte=30, v0=100.0, semilla=SEMILLA)

    primero = simular_cartera(tabla, pesos, **opciones)
    segundo = simular_cartera(tabla, pesos, **opciones)

    assert isinstance(primero, SimulationResult)
    assert primero.trayectorias.shape == (200, 31)
    np.testing.assert_allclose(primero.trayectorias[:, 0], 100.0)
    np.testing.assert_array_equal(primero.trayectorias, segundo.trayectorias)


def test_cartera_de_javi_alimenta_el_motor(precios_dos_calendarios):
    series = [
        SeriePrecios(ticker, precios, fuente="sintetica", moneda="USD")
        for ticker, precios in precios_dos_calendarios.items()
    ]
    cartera = Cartera("SintÃ©tica", series, {"AAA": 0.5, "BBB": 0.5})

    tabla, _ = alinear_precios(cartera.obtener_precios())
    resultado = simular_cartera(
        tabla, cartera.obtener_pesos(), n_sims=100, horizonte=20, semilla=SEMILLA,
        nombre=cartera.nombre,
    )

    assert resultado.nombre == "SintÃ©tica"
    assert resultado.trayectorias.shape == (100, 21)
    assert np.isfinite(resultado.trayectorias).all()
    assert resultado.parametros["pesos"] == pytest.approx({"AAA": 0.5, "BBB": 0.5})


def test_plot_no_falla_con_backend_agg(precios_dos_calendarios):
    tabla, _ = alinear_precios(precios_dos_calendarios)
    resultado = simular_cartera(
        tabla, {"AAA": 0.5, "BBB": 0.5}, n_sims=50, horizonte=10, semilla=SEMILLA
    )

    figura = resultado.plot(mostrar=False)
    try:
        assert len(figura.axes) == 2  # trayectorias + distribuciÃ³n del valor final
    finally:
        plt.close(figura)
