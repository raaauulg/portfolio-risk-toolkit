"""Pruebas automáticas del motor de Monte Carlo con t de Student.

Ejecutar desde la carpeta principal del proyecto:
    python -m pytest tests/test_montecarlo.py -v
"""

import matplotlib

matplotlib.use("Agg")  # los gráficos no abren ventanas durante las pruebas

import numpy as np
import pandas as pd
import pytest
from matplotlib.figure import Figure

from miax_toolkit.montecarlo import (
    SimulationResult,
    _factor_cholesky,
    _shocks_t_student,
    estimar_parametros,
    simular_activo,
    simular_cartera,
)


# ---------- Datos de prueba ----------

@pytest.fixture
def precios():
    """Tres activos inventados y correlacionados, siempre los mismos (semilla fija)."""
    generador = np.random.default_rng(5)
    fechas = pd.bdate_range("2022-01-03", periods=750)
    correlacion = np.array([[1.0, 0.6, 0.2], [0.6, 1.0, 0.3], [0.2, 0.3, 1.0]])
    vol_diaria = np.array([0.020, 0.015, 0.008])
    cov = np.outer(vol_diaria, vol_diaria) * correlacion
    rend = generador.multivariate_normal([0.0004, 0.0003, 0.0001], cov, len(fechas))
    return pd.DataFrame(100 * np.exp(rend.cumsum(axis=0)), index=fechas,
                        columns=["TEC", "BANCO", "BONOS"])


@pytest.fixture
def pesos():
    return {"TEC": 0.5, "BANCO": 0.3, "BONOS": 0.2}


# ---------- 1. Forma y parámetros básicos ----------

def test_forma_de_las_trayectorias(precios, pesos):
    r = simular_cartera(precios, pesos, n_sims=200, horizonte=30)
    assert isinstance(r, SimulationResult)
    assert r.trayectorias.shape == (200, 31)  # 30 días + el valor inicial


def test_todas_las_trayectorias_empiezan_en_v0(precios, pesos):
    r = simular_cartera(precios, pesos, n_sims=100, horizonte=10, v0=1000)
    assert (r.trayectorias[:, 0] == 1000).all()


def test_los_valores_son_siempre_positivos(precios, pesos):
    r = simular_cartera(precios, pesos, n_sims=2000, horizonte=252)
    assert np.isfinite(r.trayectorias).all()
    assert (r.trayectorias > 0).all()


def test_activo_parte_de_su_ultimo_precio(precios):
    r = simular_activo(precios["BANCO"], n_sims=10, horizonte=5)
    assert r.valor_inicial == pytest.approx(precios["BANCO"].iloc[-1])
    assert r.nombre == "BANCO"


# ---------- 2. Reproducibilidad ----------

def test_misma_semilla_mismo_resultado(precios, pesos):
    a = simular_cartera(precios, pesos, n_sims=100, horizonte=20, semilla=7)
    b = simular_cartera(precios, pesos, n_sims=100, horizonte=20, semilla=7)
    np.testing.assert_array_equal(a.trayectorias, b.trayectorias)


def test_distinta_semilla_distinto_resultado(precios, pesos):
    a = simular_cartera(precios, pesos, n_sims=100, horizonte=20, semilla=1)
    b = simular_cartera(precios, pesos, n_sims=100, horizonte=20, semilla=2)
    assert not np.allclose(a.trayectorias, b.trayectorias)


# ---------- 3. El motor reproduce la teoría ----------

def test_media_y_desviacion_del_log_coinciden_con_la_teoria(precios):
    # Teoría: media de ln(V_T / V0) = mu * T  y  desviación = sigma * raiz(T)
    mu, sigma = 0.08, 0.20
    r = simular_activo(precios["TEC"], v0=100, retorno=mu, volatilidad=sigma,
                       n_sims=100_000, horizonte=252, semilla=1)
    log_final = np.log(r.valores_finales / 100)
    assert log_final.mean() == pytest.approx(mu, abs=0.003)
    assert log_final.std() == pytest.approx(sigma, rel=0.01)


def test_volatilidad_cero_da_un_resultado_fijo(precios):
    # Sin volatilidad no hay azar: V_T = V0 * exp(mu * T) en todos los escenarios
    r = simular_activo(precios["TEC"], v0=100, retorno=0.05, volatilidad=0.0,
                       n_sims=50, horizonte=252)
    np.testing.assert_allclose(r.valores_finales, 100 * np.exp(0.05))


def test_la_t_de_student_tiene_colas_mas_gruesas_que_una_normal(precios):
    # Curtosis en exceso de los rendimientos diarios: 0 en una normal, 6 / (nu - 4) en una t
    r = simular_activo(precios["TEC"], v0=100, retorno=0.0, volatilidad=0.2,
                       n_sims=200_000, horizonte=1, nu=6, semilla=3)
    x = np.log(r.valores_finales / 100)
    curtosis_exceso = ((x - x.mean()) ** 4).mean() / x.var() ** 2 - 3
    assert curtosis_exceso > 1.5  # teoría: 3; una normal daría 0


def test_nu_grande_se_parece_a_una_normal(precios):
    r = simular_activo(precios["TEC"], v0=100, retorno=0.0, volatilidad=0.2,
                       n_sims=200_000, horizonte=1, nu=1000, semilla=3)
    x = np.log(r.valores_finales / 100)
    curtosis_exceso = ((x - x.mean()) ** 4).mean() / x.var() ** 2 - 3
    assert abs(curtosis_exceso) < 0.1


def test_shocks_correlacionados_y_estandarizados(precios):
    # Los shocks deben tener la correlación histórica y varianza 1
    _, _, correlacion = estimar_parametros(precios[["TEC", "BANCO"]])
    generador = np.random.default_rng(0)
    z = _shocks_t_student(generador, 300_000, _factor_cholesky(correlacion), nu=5)
    assert np.corrcoef(z.T)[0, 1] == pytest.approx(correlacion.iloc[0, 1], abs=0.01)
    assert z.var(axis=0) == pytest.approx([1.0, 1.0], abs=0.02)  # t estandarizada


# ---------- 4. Supuestos del usuario ----------

def test_por_defecto_usa_el_historico(precios, pesos):
    mu, sigma, _ = estimar_parametros(precios)
    r = simular_cartera(precios, pesos, n_sims=10, horizonte=5)
    assert r.parametros["retorno"]["TEC"] == pytest.approx(mu["TEC"])
    assert r.parametros["volatilidad"]["BONOS"] == pytest.approx(sigma["BONOS"])


def test_un_numero_se_aplica_a_todos(precios, pesos):
    r = simular_cartera(precios, pesos, n_sims=10, horizonte=5, retorno=0.04, volatilidad=0.1)
    assert set(r.parametros["retorno"].values()) == {0.04}
    assert set(r.parametros["volatilidad"].values()) == {0.1}


def test_un_diccionario_cambia_solo_esos_activos(precios, pesos):
    mu, _, _ = estimar_parametros(precios)
    r = simular_cartera(precios, pesos, n_sims=10, horizonte=5, retorno={"TEC": 0.15})
    assert r.parametros["retorno"]["TEC"] == 0.15
    assert r.parametros["retorno"]["BANCO"] == pytest.approx(mu["BANCO"])


def test_comprar_y_mantener_es_la_suma_de_los_activos(precios):
    # Sin volatilidad: V_T = V0 * suma(peso_i * exp(mu_i * T))
    r = simular_cartera(precios, {"TEC": 0.5, "BANCO": 0.3, "BONOS": 0.2}, n_sims=5,
                        horizonte=252, retorno={"TEC": 0.10, "BANCO": 0.02, "BONOS": 0.0},
                        volatilidad=0.0)
    teoria = 100 * (0.5 * np.exp(0.10) + 0.3 * np.exp(0.02) + 0.2)
    np.testing.assert_allclose(r.valores_finales, teoria)


# ---------- 5. Resumen e interpretación ----------

def test_resumen_tiene_todo_y_es_coherente(precios, pesos):
    r = simular_cartera(precios, pesos, n_sims=5000, horizonte=252)
    res = r.resumen()
    for clave in ("valor_inicial", "P5", "P50", "P95", "valor_esperado", "prob_perdida"):
        assert clave in res
    assert res["P5"] <= res["P50"] <= res["P95"]
    assert 0 <= res["prob_perdida"] <= 1


def test_percentiles_ordenados_cada_dia(precios, pesos):
    p = simular_cartera(precios, pesos, n_sims=2000, horizonte=60).percentiles()
    assert len(p) == 61
    assert (p["P5"] <= p["P50"]).all() and (p["P50"] <= p["P95"]).all()


def test_interpretacion_en_texto(precios, pesos):
    texto = simular_cartera(precios, pesos, n_sims=500, horizonte=20).interpretacion()
    assert "P5" in texto and "P95" in texto and "no una predicción" in texto


# ---------- 6. Gráfico ----------

def test_plot_devuelve_figura_y_guarda_archivo(precios, pesos, tmp_path):
    destino = tmp_path / "mc.png"
    figura = simular_cartera(precios, pesos, n_sims=300, horizonte=30).plot(mostrar=False, ruta=destino)
    assert isinstance(figura, Figure)
    assert destino.exists()


# ---------- 7. Errores claros ----------

@pytest.mark.parametrize("opciones, mensaje", [
    ({"nu": 2}, "nu"),
    ({"nu": 1.5}, "nu"),
    ({"n_sims": 0}, "n_sims"),
    ({"horizonte": 0}, "horizonte"),
    ({"v0": -10}, "v0"),
    ({"volatilidad": -0.1}, "negativa"),
    ({"retorno": {"XXX": 0.1}}, "desconocidos"),
])
def test_parametros_invalidos(precios, pesos, opciones, mensaje):
    with pytest.raises(ValueError, match=mensaje):
        simular_cartera(precios, pesos, **{"n_sims": 10, "horizonte": 5, **opciones})


def test_pesos_que_no_suman_uno(precios):
    with pytest.raises(ValueError, match="suman"):
        simular_cartera(precios, {"TEC": 0.5, "BANCO": 0.5, "BONOS": 0.5})


def test_activo_duplicado_da_error_de_cholesky(precios):
    gemelos = pd.DataFrame({"A": precios["TEC"], "B": precios["TEC"]})
    with pytest.raises(ValueError, match="definida positiva"):
        simular_cartera(gemelos, {"A": 0.5, "B": 0.5})
