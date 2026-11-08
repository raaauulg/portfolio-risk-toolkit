"""Pruebas del motor de Monte Carlo integrado en Cartera y SeriePrecios (4.4).

Datos sintéticos con semilla fija y sin Internet.
"""

import numpy as np
import pandas as pd
import pytest

from miax_toolkit import Cartera, SeriePrecios, SimulationResult, simular_activo

SEMILLA = 7
DIAS_POR_ANIO = 252


def _serie(ticker: str, fechas: pd.DatetimeIndex, semilla: int) -> SeriePrecios:
    """Paseo aleatorio geométrico: rendimientos log diarios ~ N(0.0003, 0.01)."""
    rng = np.random.default_rng(semilla)
    precios = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, len(fechas)))), index=fechas)
    return SeriePrecios(ticker, precios, fuente="sintetica", moneda="USD")


@pytest.fixture
def series() -> list[SeriePrecios]:
    fechas = pd.bdate_range("2024-01-01", periods=250)
    return [_serie(t, fechas, SEMILLA + i) for i, t in enumerate(["AAA", "BBB", "CCC"])]


@pytest.fixture
def cartera(series) -> Cartera:
    return Cartera("Sintética", series, {"AAA": 0.5, "BBB": 0.3, "CCC": 0.2})


# Reproducibilidad y forma

def test_misma_semilla_mismas_trayectorias_y_distinta_semilla_distintas(cartera):
    opciones = dict(n_sims=300, horizonte=40)
    a = cartera.monte_carlo(semilla=1, **opciones)
    b = cartera.monte_carlo(semilla=1, **opciones)
    c = cartera.monte_carlo(semilla=2, **opciones)

    np.testing.assert_array_equal(a.trayectorias, b.trayectorias)
    assert not np.array_equal(a.trayectorias, c.trayectorias)


def test_forma_y_valor_inicial_de_la_cartera(cartera):
    resultado = cartera.monte_carlo(n_sims=200, horizonte=30, v0=1_000.0)

    assert isinstance(resultado, SimulationResult)
    assert resultado.nombre == "Sintética"
    assert resultado.trayectorias.shape == (200, 31)
    np.testing.assert_allclose(resultado.trayectorias[:, 0], 1_000.0)
    assert "limpieza" in resultado.parametros


def test_serie_precios_delega_en_simular_activo(series):
    activo = series[0]
    resultado = activo.monte_carlo(n_sims=100, horizonte=10, semilla=SEMILLA)
    directo = simular_activo(activo.precios, n_sims=100, horizonte=10, semilla=SEMILLA)

    assert resultado.nombre == "AAA"
    assert resultado.trayectorias.shape == (100, 11)
    assert resultado.valor_inicial == pytest.approx(activo.precios.iloc[-1])
    np.testing.assert_array_equal(resultado.trayectorias, directo.trayectorias)


def test_serie_precios_ignora_nan_finales(series):
    precios = series[0].precios.copy()
    precios.iloc[-1] = np.nan  # SeriePrecios admite NaN sueltos
    activo = SeriePrecios("AAA", precios, fuente="sintetica")

    resultado = activo.monte_carlo(n_sims=50, horizonte=5)

    assert resultado.valor_inicial == pytest.approx(precios.iloc[-2])
    assert np.isfinite(resultado.trayectorias).all()


# Validez estadística del motor

def test_mediana_del_log_valor_final_coincide_con_la_teoria(series):
    """Para un activo, log(V_T) = log(v0) + mu*T + suma de shocks simétricos.

    La suma de t de Student simétricas es simétrica, así que su mediana es 0 y
    la mediana de log(V_T) es exactamente log(v0) + mu*T. No se usa la media:
    con shocks t de Student, E[exp(suma)] es infinita y la media muestral de
    V_T no converge de forma fiable.
    """
    retorno, horizonte, v0 = 0.08, 252, 100.0
    resultado = series[0].monte_carlo(
        n_sims=20_000, horizonte=horizonte, retorno=retorno, volatilidad=0.20,
        nu=5, v0=v0, semilla=SEMILLA,
    )

    teorica = np.log(v0) + retorno * horizonte / DIAS_POR_ANIO
    mediana = np.median(np.log(resultado.valores_finales))
    # Error típico de la mediana ~ 1.25 * 0.20 / sqrt(20000) ~ 0.002: tolerancia ~5 errores.
    assert mediana == pytest.approx(teorica, abs=0.01)


# Pesos y calendarios

def test_orden_de_los_pesos_no_cambia_el_resultado(series):
    a = Cartera("X", series, {"AAA": 0.5, "BBB": 0.3, "CCC": 0.2})
    b = Cartera("X", series, {"CCC": 0.2, "AAA": 0.5, "BBB": 0.3})

    ra = a.monte_carlo(n_sims=200, horizonte=20)
    rb = b.monte_carlo(n_sims=200, horizonte=20)

    np.testing.assert_array_equal(ra.trayectorias, rb.trayectorias)


def test_calendarios_distintos_se_alinean_y_simulan():
    habiles = pd.bdate_range("2024-01-01", periods=250)
    sin_lunes = habiles[habiles.day_of_week != 0]
    cartera = Cartera(
        "Dos bolsas",
        [_serie("AAA", habiles, 1), _serie("BBB", sin_lunes, 2)],
        {"AAA": 0.5, "BBB": 0.5},
    )

    resultado = cartera.monte_carlo(n_sims=100, horizonte=10)

    assert np.isfinite(resultado.trayectorias).all()
    assert any("Alineación" in linea for linea in resultado.parametros["limpieza"])


# Divisas: no se convierten, así que una cartera con varias monedas se rechaza.

def test_cartera_que_mezcla_divisas_da_error():
    fechas = pd.bdate_range("2024-01-01", periods=100)
    usd = _serie("AAPL", fechas, 1)  # moneda="USD"
    eur = SeriePrecios("SAN.MC", _serie("X", fechas, 2).precios, fuente="sintetica", moneda="EUR")
    cartera = Cartera("Mixta", [usd, eur], {"AAPL": 0.5, "SAN.MC": 0.5})

    with pytest.raises(ValueError, match="mezcla monedas"):
        cartera.monte_carlo(n_sims=50, horizonte=5)


def test_activo_sin_moneda_da_error(series):
    sin_moneda = SeriePrecios("ZZZ", series[1].precios, fuente="sintetica")
    cartera = Cartera("Incompleta", [series[0], sin_moneda], {"AAA": 0.5, "ZZZ": 0.5})

    with pytest.raises(ValueError, match="Falta la moneda"):
        cartera.monte_carlo(n_sims=50, horizonte=5)


# Errores

def test_nu_menor_o_igual_que_2_da_error(cartera):
    with pytest.raises(ValueError, match="nu"):
        cartera.monte_carlo(nu=2)


def test_horizonte_cero_da_error(cartera):
    with pytest.raises(ValueError, match="horizonte"):
        cartera.monte_carlo(horizonte=0)


def test_menos_de_min_observaciones_da_error():
    fechas = pd.bdate_range("2024-01-01", periods=20)
    cartera = Cartera("Corta", [_serie("AAA", fechas, 1)], {"AAA": 1.0})

    with pytest.raises(ValueError, match="al menos 30"):
        cartera.monte_carlo()


def test_correlacion_perfecta_se_admite(series):
    # Mismos precios con otro ticker: correlación 1. Cholesky falla, pero la
    # matriz es semidefinida positiva y el motor usa su descomposición espectral.
    copia = SeriePrecios("AAA_BIS", series[0].precios.copy(), fuente="sintetica", moneda="USD")
    cartera = Cartera("Duplicada", [series[0], copia], {"AAA": 0.5, "AAA_BIS": 0.5})

    resultado = cartera.monte_carlo(n_sims=100, horizonte=5)

    assert np.isfinite(resultado.trayectorias).all()
