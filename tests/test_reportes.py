"""Pruebas de report() y plots_report() de la cartera (apartado 4.5).

Datos sintéticos con semilla fija y sin Internet.
"""

import matplotlib

matplotlib.use("Agg")  # backend sin ventana: los tests no abren gráficos

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from miax_toolkit import Cartera, SeriePrecios

GRAFICOS = ("rendimiento", "correlacion", "evolucion", "riesgo")


@pytest.fixture
def cartera() -> Cartera:
    fechas = pd.bdate_range("2024-01-01", periods=300)
    rng = np.random.default_rng(11)
    series = [
        SeriePrecios(t, pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, 300))), index=fechas),
                     fuente="sintetica", moneda="USD")
        for t in ("AAA", "BBB", "CCC")
    ]
    return Cartera("Sintética", series, {"AAA": 0.5, "BBB": 0.3, "CCC": 0.2})


def test_report_completo_en_markdown(cartera):
    texto = cartera.report(simulacion=cartera.monte_carlo(n_sims=200, horizonte=20))

    for titulo in ("## Métricas de la cartera", "## Composición", "## Correlaciones",
                   "## Simulación de Monte Carlo", "## Diagnóstico de los datos",
                   "## Advertencias de riesgo"):
        assert titulo in texto, titulo


def test_report_solo_las_secciones_pedidas(cartera):
    texto = cartera.report(secciones=("resumen",))

    assert "## Métricas de la cartera" in texto
    assert "## Correlaciones" not in texto
    with pytest.raises(ValueError, match="Secciones desconocidas"):
        cartera.report(secciones=("inventada",))


def test_report_rechaza_la_simulacion_de_otra_cartera(cartera):
    otra = Cartera("Otra", cartera.series, {"AAA": 0.2, "BBB": 0.3, "CCC": 0.5})
    simulacion_ajena = otra.monte_carlo(n_sims=50, horizonte=5)

    with pytest.raises(ValueError, match="corresponder a esta cartera"):
        cartera.report(simulacion=simulacion_ajena)


def test_plots_report_devuelve_y_guarda_los_cuatro_graficos(cartera, tmp_path):
    figuras = cartera.plots_report(mostrar=False, carpeta=tmp_path)
    try:
        assert tuple(figuras) == GRAFICOS
        assert all((tmp_path / f"{nombre}.png").exists() for nombre in GRAFICOS)
    finally:
        for figura in figuras.values():
            plt.close(figura)


def test_plots_report_grafico_desconocido_da_error(cartera):
    with pytest.raises(ValueError, match="Gráficos desconocidos"):
        cartera.plots_report(graficos=("inventado",), mostrar=False)
