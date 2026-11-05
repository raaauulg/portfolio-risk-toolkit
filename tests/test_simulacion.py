import numpy as np
import pandas as pd
import pytest

from miax_toolkit.limpieza import ErrorValidacion
from miax_toolkit.metricas import rendimientos_log
from miax_toolkit.simulacion import ParametrosSimulacion, simular_activo, simular_cartera


def test_forma_y_valor_inicial(precios, pesos):
    p = ParametrosSimulacion(n_iteraciones=50, horizonte_dias=20, valor_inicial=1000, semilla=1)
    r = simular_cartera(precios, pesos, p)
    assert r.trayectorias.shape == (50, 21)
    assert (r.trayectorias[:, 0] == 1000).all()


def test_misma_semilla_mismo_resultado(precios, pesos):
    p = ParametrosSimulacion(n_iteraciones=100, horizonte_dias=10, semilla=7)
    np.testing.assert_array_equal(simular_cartera(precios, pesos, p).trayectorias,
                                  simular_cartera(precios, pesos, p).trayectorias)


def test_valor_esperado_y_volatilidad_coinciden_con_la_teoria(precios):
    # Teoría: E[S(1)] = S(0) * exp(mu); desviación de ln(S(1)/S(0)) = sigma
    p = ParametrosSimulacion(n_iteraciones=200_000, horizonte_dias=252, retorno_anual=0.08,
                             volatilidad_anual=0.20, valor_inicial=100, semilla=3)
    r = simular_activo(precios["AAA"], p)
    assert r.valores_finales.mean() == pytest.approx(100 * np.exp(0.08), rel=0.003)
    assert np.log(r.valores_finales / 100).std() == pytest.approx(0.20, rel=0.005)


def test_volatilidad_cero_es_determinista(precios):
    p = ParametrosSimulacion(n_iteraciones=5, horizonte_dias=252, retorno_anual=0.05,
                             volatilidad_anual=0.0, valor_inicial=100, semilla=1)
    finales = simular_activo(precios["AAA"], p).valores_finales
    np.testing.assert_allclose(finales, 100 * np.exp(0.05))


def test_estimacion_historica_reproduce_media_y_volatilidad(precios):
    r = simular_activo(precios["AAA"], ParametrosSimulacion(n_iteraciones=2, horizonte_dias=1, semilla=1))
    log = rendimientos_log(precios["AAA"])
    sigma = log.std() * np.sqrt(252)
    assert r.supuestos["volatilidad_anual"].iloc[0] == pytest.approx(sigma)
    assert r.supuestos["retorno_anual"].iloc[0] == pytest.approx(log.mean() * 252 + sigma**2 / 2)


def test_activo_parte_del_ultimo_precio(precios):
    r = simular_activo(precios["BBB"], ParametrosSimulacion(n_iteraciones=2, horizonte_dias=2, semilla=1))
    assert r.valor_inicial == pytest.approx(precios["BBB"].iloc[-1])


def test_cartera_de_un_activo_equivale_a_ese_activo(precios):
    p = ParametrosSimulacion(n_iteraciones=100, horizonte_dias=30, valor_inicial=100, semilla=2)
    a = simular_activo(precios["AAA"], p)
    b = simular_cartera(precios[["AAA"]], {"AAA": 1.0}, p)
    np.testing.assert_allclose(a.trayectorias, b.trayectorias)


def test_conserva_la_correlacion_entre_activos(precios):
    # Con vol iguales y rebalanceo diario, la varianza de una cartera 50/50 es
    # sigma^2 * (1 + rho) / 2; la vol simulada debe reflejar la correlación real.
    pares = precios[["AAA", "BBB"]]
    rho = rendimientos_log(pares).corr().iloc[0, 1]
    p = ParametrosSimulacion(n_iteraciones=100_000, horizonte_dias=1, retorno_anual=0.0,
                             volatilidad_anual=0.2, valor_inicial=100, semilla=4)
    r = simular_cartera(pares, {"AAA": 0.5, "BBB": 0.5}, p)
    obtenida = (r.valores_finales / 100).std() * np.sqrt(252)
    assert obtenida == pytest.approx(0.2 * np.sqrt((1 + rho) / 2), rel=0.01)


def test_activos_identicos_no_rompen_la_correlacion(precios):
    gemelos = pd.DataFrame({"A": precios["AAA"], "B": precios["AAA"]})
    r = simular_cartera(gemelos, {"A": 0.5, "B": 0.5},
                        ParametrosSimulacion(n_iteraciones=20, horizonte_dias=5, semilla=1))
    assert np.isfinite(r.trayectorias).all()


def test_rebalanceo_no_cambia_el_inicio_y_ambos_modos_funcionan(precios, pesos):
    base = dict(n_iteraciones=2000, horizonte_dias=252, semilla=5)
    diario = simular_cartera(precios, pesos, ParametrosSimulacion(rebalanceo="diario", **base))
    ninguno = simular_cartera(precios, pesos, ParametrosSimulacion(rebalanceo="ninguno", **base))
    assert not np.allclose(diario.valores_finales, ninguno.valores_finales)
    assert ninguno.trayectorias[0, 0] == 100


def test_compra_y_mantener_equivale_a_suma_de_activos(precios):
    p = ParametrosSimulacion(n_iteraciones=50_000, horizonte_dias=252, rebalanceo="ninguno",
                             retorno_anual={"AAA": 0.10, "BBB": 0.02, "CCC": 0.0},
                             volatilidad_anual=0.2, semilla=6)
    r = simular_cartera(precios, {"AAA": 0.5, "BBB": 0.3, "CCC": 0.2}, p)
    teoria = 100 * (0.5 * np.exp(0.10) + 0.3 * np.exp(0.02) + 0.2)
    assert r.valores_finales.mean() == pytest.approx(teoria, rel=0.005)


def test_var_cvar_y_probabilidad_son_coherentes(precios, pesos):
    r = simular_cartera(precios, pesos, ParametrosSimulacion(n_iteraciones=5000, semilla=1))
    assert r.cvar() >= r.var()
    assert 0 <= r.prob_perdida() <= 1
    p = r.percentiles()
    assert (p["p5"] <= p["p50"]).all() and (p["p50"] <= p["p95"]).all()


@pytest.mark.parametrize(
    "kwargs",
    [{"n_iteraciones": 1}, {"horizonte_dias": 0}, {"valor_inicial": -1}, {"rebalanceo": "mensual"}],
)
def test_parametros_invalidos(kwargs):
    with pytest.raises(ValueError):
        ParametrosSimulacion(**kwargs)


def test_supuestos_invalidos(precios, pesos):
    with pytest.raises(ErrorValidacion, match="desconocidos"):
        simular_cartera(precios, pesos, ParametrosSimulacion(retorno_anual={"ZZZ": 0.1}))
    with pytest.raises(ErrorValidacion, match="menor"):
        simular_cartera(precios, pesos, ParametrosSimulacion(volatilidad_anual=-0.1))
