"""La orquestación del dashboard muestra exactamente las cifras del toolkit."""

from dataclasses import replace
import re

import numpy as np
import pytest

from app.analisis import calcular, extraer_advertencias
from app.configuracion import NU_CASI_NORMAL, PRESETS
from app.datos import recortar


def _celda(informe: str, metrica: str) -> str:
    """Valor de la tabla «Métricas de la cartera» del Markdown de report()."""
    coincidencia = re.search(rf"^\| {re.escape(metrica)}[^|]* \| ([^|]+) \|$", informe, re.MULTILINE)
    assert coincidencia, metrica
    return coincidencia.group(1).strip()


def _pct2(x: float) -> str:
    return f"{x * 100:.2f} %".replace(".", ",")


@pytest.mark.parametrize("clave", list(PRESETS))
def test_los_kpi_coinciden_con_el_informe_del_toolkit(calcular_preset, clave):
    res = calcular_preset(clave)
    m, informe = res.metricas, res.informe
    assert _celda(informe, "Rentabilidad anualizada") == _pct2(m["rent_anual"])
    assert _celda(informe, "Volatilidad anualizada") == _pct2(m["volatilidad"])
    assert _celda(informe, "Caída máxima") == _pct2(m["caida_maxima"])
    assert _celda(informe, "VaR diario histórico") == _pct2(m["var"])
    assert _celda(informe, "CVaR diario histórico") == _pct2(m["cvar"])
    assert _celda(informe, "Ratio de Sharpe") == f"{m['sharpe']:.2f}".replace(".", ",")
    assert f"{len(res.tabla_analisis)} sesiones" in informe


@pytest.mark.parametrize("clave, moneda", [("demo", "USD"), ("eeuu", "USD"), ("europa", "EUR")])
def test_cada_preset_usa_una_sola_moneda(calcular_preset, clave, moneda):
    res = calcular_preset(clave)
    assert res.moneda == moneda
    assert set(res.cartera.obtener_monedas().values()) == {moneda}


def test_comparador_de_colas_usa_la_misma_semilla_y_otro_nu(calcular_preset):
    res = calcular_preset("demo")
    t, normal = res.simulacion.parametros, res.simulacion_normal.parametros
    assert t["semilla"] == normal["semilla"] and t["n_sims"] == normal["n_sims"]
    assert (t["nu"], normal["nu"]) == (PRESETS["demo"].config.nu, NU_CASI_NORMAL)
    # A un día, colas más gruesas: extremos más alejados con el nu pequeño.
    # (A un año casi desaparecen: la suma de 252 shocks independientes tiende a la normal.)
    t_dia1 = res.simulacion.percentiles((0.1, 99.9)).iloc[1]
    n_dia1 = res.simulacion_normal.percentiles((0.1, 99.9)).iloc[1]
    assert t_dia1["P0.1"] < n_dia1["P0.1"] and t_dia1["P99.9"] > n_dia1["P99.9"]


def test_parametros_historicos_son_los_de_la_simulacion(calcular_preset):
    res = calcular_preset("demo")
    for activo in res.config.activos:
        assert res.simulacion.parametros["retorno"][activo] == pytest.approx(res.mu[activo])
        assert res.simulacion.parametros["volatilidad"][activo] == pytest.approx(res.sigma[activo])


def test_el_benchmark_se_cruza_por_fechas_sin_rellenar(calcular_preset):
    res = calcular_preset("europa")  # el Euro Stoxx 50 de la instantánea tiene menos sesiones
    assert len(res.tabla_analisis) < len(res.tabla)
    assert res.tabla_analisis.index.equals(res.referencia.index)
    assert res.valores_ref.iloc[0] == pytest.approx(100.0)


def test_extraer_advertencias_del_markdown():
    informe = "## Advertencias de riesgo\n\n- **ALTO:** Concentración: X.\n- **INFO:** Aviso fijo.\n"
    assert extraer_advertencias(informe) == [("ALTO", "Concentración: X."), ("INFO", "Aviso fijo.")]
    assert extraer_advertencias("# Sin sección") == []


def _series_de(instantanea, config):
    series, _ = instantanea
    return {a: recortar(series[a], config.inicio, config.fin) for a in config.activos}


def test_pesos_invalidos_dan_el_error_del_toolkit(instantanea):
    config = replace(PRESETS["demo"].config, pesos=(0.5, 0.2, 0.2, 0.2, 0.15), benchmark=None)
    with pytest.raises(ValueError, match="deben sumar 1"):
        calcular(config, _series_de(instantanea, config))


def test_mezclar_monedas_da_el_error_del_toolkit(instantanea):
    config = replace(PRESETS["demo"].config, activos=("AAPL", "SAN.MC"), pesos=(0.5, 0.5), benchmark=None)
    with pytest.raises(ValueError, match="mezcla monedas"):
        calcular(config, _series_de(instantanea, config))


def test_resultados_son_finitos(calcular_preset):
    res = calcular_preset("demo")
    assert np.isfinite(res.simulacion.trayectorias).all()
    assert res.riesgo.sum() == pytest.approx(1.0)
