"""Las funciones de app/graficos.py devuelven figuras completas: trazas, títulos, ejes con unidades y formato."""

import pandas as pd
import plotly.graph_objects as go
import pytest

from miax_toolkit.reportes import valor_cartera

from app import estilo, graficos, transformaciones


@pytest.fixture(scope="module")
def res(calcular_preset):
    return calcular_preset("demo")


def _comprobar(figura, titulo: str, eje_x: str | None, eje_y: str | None):
    assert isinstance(figura, go.Figure)
    assert titulo in figura.layout.title.text
    assert figura.layout.separators == ",."
    if eje_x:
        assert eje_x in figura.layout.xaxis.title.text
    if eje_y:
        assert eje_y in figura.layout.yaxis.title.text


def test_evolucion_frente_al_benchmark(res):
    figura = graficos.evolucion(res.valores, res.valores_ref, res.config.nombre, res.nombre_ref)
    _comprobar(figura, "frente a S&P 500", "Fecha", "base 100")
    assert [t.name for t in figura.data] == ["S&P 500", res.config.nombre]
    assert figura.data[0].line.dash == "dash"  # el benchmark no se distingue solo por color


def test_precios_base100_un_color_fijo_por_activo(res):
    tabla = pd.DataFrame({a: valor_cartera(res.tabla[[a]], {a: 1.0}) for a in res.tabla.columns})
    figura = graficos.precios_base100(tabla)
    _comprobar(figura, "base 100", "Fecha", "Precio (base 100)")
    colores = estilo.colores_activos(res.config.activos)
    assert {t.name: t.line.color for t in figura.data} == colores


def test_composicion_y_riesgo(res):
    pesos = pd.Series(res.cartera.obtener_pesos())
    composicion = graficos.composicion(pesos)
    _comprobar(composicion, "Composición", "%", None)
    assert sorted(composicion.data[0].y) == sorted(res.config.activos)
    riesgo = graficos.peso_vs_riesgo(pesos, res.riesgo)
    assert [t.name for t in riesgo.data] == ["Peso", "Aportación al riesgo"]
    assert riesgo.data[1].marker.pattern.shape == "/"  # trama: codificación además del color


def test_correlacion_escala_fija_y_valores_escritos(res):
    figura = graficos.correlacion(res.correlacion)
    _comprobar(figura, "Correlación", None, None)
    mapa = figura.data[0]
    assert (mapa.zmin, mapa.zmax) == (-1, 1)
    assert mapa.text[0][0] == "1,00"


def test_caidas_volatilidad_y_distribucion(res):
    caidas = graficos.caidas(transformaciones.caidas(res.valores))
    _comprobar(caidas, "drawdown", "Fecha", "(%)")
    assert "Máxima" in caidas.layout.annotations[0].text
    vol = graficos.volatilidad_movil(transformaciones.volatilidad_movil(res.valores, 63), 63)
    _comprobar(vol, "63 sesiones", "Fecha", "Volatilidad anualizada (%)")
    dist = graficos.distribucion_rendimientos(transformaciones.rendimientos(res.valores),
                                              res.metricas["var"], res.metricas["cvar"], 0.95)
    _comprobar(dist, "rentabilidades diarias", "Rentabilidad diaria (%)", "Número de días")
    textos = [a.text for a in dist.layout.annotations]
    assert any(t.startswith("VaR 95 %") for t in textos) and any(t.startswith("CVaR 95 %") for t in textos)


def test_figuras_de_monte_carlo(res):
    sim, r = res.simulacion, res.simulacion.resumen()
    abanico = graficos.abanico(sim.percentiles((5, 25, 50, 75, 95)), sim.trayectorias[:10],
                               sim.valor_inicial, "USD")
    _comprobar(abanico, "abanico", "Días de mercado", "Valor de la cartera (USD)")
    nombres = {t.name for t in abanico.data if t.showlegend is not False}
    assert {"Entre P5 y P95", "Entre P25 y P75", "Mediana (P50)", "10 trayectorias"} <= nombres

    extremos = sim.percentiles((1, 99)).iloc[-1]
    histograma = graficos.histograma_final(sim.valores_finales, r, (extremos["P1"], extremos["P99"]), "USD")
    _comprobar(histograma, "P1 y P99", "Valor final (USD)", "Número de escenarios")
    assert [a.text for a in histograma.layout.annotations] == ["P5", "P50", "P95", "Inicial"]

    colas = graficos.comparador_colas(sim.trayectorias[:, 1], res.simulacion_normal.trayectorias[:, 1], 5, 200,
                                      (extremos["P1"], extremos["P99"]), "USD", 1)
    _comprobar(colas, "colas en el día 1", "día 1 (USD)", "% de escenarios")
    assert [t.line.dash for t in colas.data] == ["dash", "solid"]
    assert colas.layout.yaxis.type == "log"


@pytest.mark.parametrize("perdida, etiqueta, posicion", [
    (0.02, "-2,0 %", -2.0),
    (-0.001, "0,1 %", 0.1),
])
def test_var_y_cvar_muestran_el_rendimiento_con_el_signo_correcto(perdida, etiqueta, posicion):
    figura = graficos.distribucion_rendimientos(pd.Series([-.02, .001, .03]),
                                                perdida, perdida, .95)
    assert [a.text for a in figura.layout.annotations] == [
        f"VaR 95 %: {etiqueta}", f"CVaR 95 %: {etiqueta}"]
    assert [linea.x0 for linea in figura.layout.shapes] == pytest.approx([posicion, posicion])


def test_tema_oscuro_cambia_los_colores_de_serie(res):
    claro = graficos.volatilidad_movil(transformaciones.volatilidad_movil(res.valores, 21), 21, "claro")
    oscuro = graficos.volatilidad_movil(transformaciones.volatilidad_movil(res.valores, 21), 21, "oscuro")
    assert claro.data[0].line.color != oscuro.data[0].line.color


def test_mas_de_ocho_activos_no_recicla_colores():
    with pytest.raises(ValueError, match="8 activos"):
        estilo.colores_activos([f"A{i}" for i in range(9)])
