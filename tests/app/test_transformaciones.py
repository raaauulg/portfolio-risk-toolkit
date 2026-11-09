"""app/transformaciones.py reproduce las series que calcula y dibuja el toolkit."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from miax_toolkit import Cartera, SeriePrecios, alinear_precios
from miax_toolkit.reportes import metricas, valor_cartera

from app import transformaciones


@pytest.fixture(scope="module")
def cartera() -> Cartera:
    fechas = pd.bdate_range("2023-01-02", periods=400)
    rng = np.random.default_rng(3)
    series = [SeriePrecios(t, pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.012, 400))), index=fechas),
                           fuente="sintetica", moneda="EUR") for t in ("AAA", "BBB", "CCC")]
    return Cartera("Sintética", series, {"AAA": 0.5, "BBB": 0.3, "CCC": 0.2})


@pytest.fixture(scope="module")
def valores(cartera) -> pd.Series:
    tabla, _ = alinear_precios(cartera.obtener_precios())
    return valor_cartera(tabla, cartera.obtener_pesos())


def test_caidas_coinciden_con_la_figura_y_las_metricas_del_toolkit(cartera, valores):
    figura = cartera.plots_report(graficos=("evolucion",), mostrar=False)["evolucion"]
    try:
        dibujada = figura.axes[1].lines[0].get_ydata()  # panel inferior: caída desde máximos en %
    finally:
        plt.close(figura)
    caidas = transformaciones.caidas(valores)
    np.testing.assert_allclose(caidas.to_numpy() * 100, dibujada)
    assert caidas.min() == pytest.approx(metricas(valores)["caida_maxima"])


@pytest.mark.parametrize("ventana", [21, 63])
def test_volatilidad_movil_coincide_con_la_figura_de_riesgo(cartera, valores, ventana):
    figura = cartera.plots_report(graficos=("riesgo",), ventana_volatilidad=ventana, mostrar=False)["riesgo"]
    try:
        dibujada = figura.axes[0].lines[0].get_ydata()  # panel izquierdo: volatilidad móvil en %
    finally:
        plt.close(figura)
    np.testing.assert_allclose(transformaciones.volatilidad_movil(valores, ventana).to_numpy() * 100, dibujada)


@pytest.mark.parametrize("nivel", [0.95, 0.99])
def test_rendimientos_reproducen_el_var_del_toolkit(valores, nivel):
    rendimientos = transformaciones.rendimientos(valores)
    m = metricas(valores, nivel_var=nivel)
    assert -rendimientos.quantile(1 - nivel) == pytest.approx(m["var"])
    assert len(rendimientos) == len(valores) - 1
