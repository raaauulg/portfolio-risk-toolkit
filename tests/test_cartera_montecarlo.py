"""Pruebas del método monte_carlo() de la Cartera."""

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pandas as pd
import pytest

from miax_toolkit import Cartera, SeriePrecios
from miax_toolkit.montecarlo import SimulationResult


@pytest.fixture
def cartera():
    generador = np.random.default_rng(5)
    fechas = pd.bdate_range("2023-01-02", periods=500)
    rend = generador.multivariate_normal([4e-4, 3e-4], [[4e-4, 1.5e-4], [1.5e-4, 2.25e-4]], 500)
    precios = 100 * np.exp(rend.cumsum(axis=0))
    aapl = SeriePrecios("AAPL", pd.Series(precios[:, 0], index=fechas), "sintético")
    msft = SeriePrecios("MSFT", pd.Series(precios[:, 1], index=fechas).drop(fechas[[3, 9]]), "sintético")
    return Cartera("Ejemplo", [aapl, msft], {"AAPL": 0.6, "MSFT": 0.4})


def test_monte_carlo_de_la_cartera(cartera):
    r = cartera.monte_carlo(n_sims=500, horizonte=60)
    assert isinstance(r, SimulationResult)
    assert r.nombre == "Ejemplo"
    assert r.trayectorias.shape == (500, 61)
    assert r.valor_inicial == 100


def test_monte_carlo_de_un_activo(cartera):
    r = cartera.monte_carlo(activo="MSFT", n_sims=200, horizonte=20)
    assert r.nombre == "MSFT"
    assert r.valor_inicial == pytest.approx(cartera.obtener_precios()["MSFT"].iloc[-1])


def test_parametros_llegan_al_motor(cartera):
    r = cartera.monte_carlo(n_sims=50, horizonte=10, retorno=0.04, volatilidad=0.2, nu=7, v0=1000)
    assert r.parametros["nu"] == 7
    assert r.valor_inicial == 1000
    assert set(r.parametros["retorno"].values()) == {0.04}


def test_misma_semilla_mismo_resultado(cartera):
    a = cartera.monte_carlo(n_sims=100, horizonte=10, semilla=3)
    b = cartera.monte_carlo(n_sims=100, horizonte=10, semilla=3)
    np.testing.assert_array_equal(a.trayectorias, b.trayectorias)


def test_activo_que_no_existe(cartera):
    with pytest.raises(ValueError, match="no está en la cartera"):
        cartera.monte_carlo(activo="XXX")
