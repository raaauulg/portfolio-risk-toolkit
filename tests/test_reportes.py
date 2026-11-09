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


@pytest.mark.parametrize("metodo", ["report", "plots_report", "monte_carlo"])
def test_cartera_revalida_tickers_tras_editar_la_lista(cartera, metodo):
    cartera.series.append(cartera.series[0])
    with pytest.raises(ValueError, match="mismo ticker"):
        getattr(cartera, metodo)()


def test_benchmark_incluye_su_limpieza_y_no_cambia_calibracion(cartera):
    r = cartera.monte_carlo(n_sims=2, horizonte=1)
    referencia = cartera.series[0].precios.iloc[50:].copy()
    referencia.iloc[10] = np.nan
    texto = cartera.report(benchmark=referencia, simulacion=r)
    assert "benchmark: 1 NA eliminado" in texto
    assert f"{r.parametros['fecha_inicio']} a {r.parametros['fecha_fin']}" in texto
    assert "Benchmark: análisis sobre 249 de 300 fechas" in texto


def test_metricas_con_resultados_calculados_a_mano():
    from miax_toolkit.reportes import metricas
    valores = pd.Series([100., 110., 99., 99.], index=pd.bdate_range("2025-01-01", periods=4))
    m = metricas(valores)
    assert m["rent_total"] == pytest.approx(-.01)
    assert m["rent_anual"] == pytest.approx(.99 ** 84 - 1)
    assert m["volatilidad"] == pytest.approx(.1 * np.sqrt(252))
    assert m["caida_maxima"] == pytest.approx(-.1)
    assert m["var"] == pytest.approx(.09)
    assert m["cvar"] == pytest.approx(.1)


def test_cartera_constante_genera_informe_y_graficos():
    fechas = pd.bdate_range("2025-01-01", periods=70)
    s = SeriePrecios("FIJO", pd.Series(100., index=fechas), "sintetica", moneda="EUR")
    c = Cartera("Constante", [s], {"FIJO": 1.})
    assert "n/d" in c.report()
    figuras = c.plots_report(mostrar=False)
    try:
        for figura in figuras.values():
            figura.canvas.draw()
    finally:
        for figura in figuras.values():
            plt.close(figura)


def test_titulo_de_correlacion_cabe_en_la_figura(cartera):
    cartera.nombre = "Cartera AAPL-MSFT"
    figura = cartera.plots_report(graficos=("correlacion",), mostrar=False)["correlacion"]
    try:
        figura.canvas.draw()
        limites = figura.axes[0]._left_title.get_window_extent(figura.canvas.get_renderer())
        assert limites.x0 >= 0 and limites.x1 <= figura.bbox.x1
        assert limites.y1 <= figura.bbox.y1
    finally:
        plt.close(figura)
