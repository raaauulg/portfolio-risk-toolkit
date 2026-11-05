import numpy as np
import pandas as pd
import pytest
from matplotlib.figure import Figure

from miax_toolkit.limpieza import ErrorValidacion
from miax_toolkit.metricas import (
    contribucion_riesgo,
    rendimientos_simples,
    retorno_anualizado,
    valor_cartera,
)
from miax_toolkit.reportes import GRAFICOS, SECCIONES, UmbralesRiesgo


def test_contribucion_riesgo_suma_uno(precios):
    r = contribucion_riesgo(rendimientos_simples(precios), pd.Series({"AAA": .5, "BBB": .3, "CCC": .2}))
    assert r.sum() == pytest.approx(1)


def test_retorno_anualizado_conocido():
    valores = pd.Series(100 * 1.1 ** (np.arange(505) / 252))
    assert retorno_anualizado(valores) == pytest.approx(0.1)


def test_valor_cartera_a_mano():
    fechas = pd.bdate_range("2024-01-01", periods=3)
    precios = pd.DataFrame({"A": [10., 20., 20.], "B": [10., 10., 20.]}, index=fechas)
    pesos = pd.Series({"A": .5, "B": .5})
    # Diario: +50 % y luego +50 %. Sin rebalanceo: 0,5*2 + 0,5*2 = 2
    assert valor_cartera(precios, pesos, "diario").iloc[-1] == pytest.approx(225)
    assert valor_cartera(precios, pesos, "ninguno").iloc[-1] == pytest.approx(200)


def test_report_incluye_todas_las_secciones(cartera):
    sim = cartera.monte_carlo(n_iteraciones=200, horizonte_dias=20, semilla=1)
    texto = cartera.report(simulacion=sim)
    for titulo in ("# Informe de Prueba", "## Resumen", "## Composición", "## Métricas por activo",
                   "## Correlaciones", "## Simulación de Monte Carlo", "## Diagnóstico de los datos",
                   "## Advertencias de riesgo"):
        assert titulo in texto


def test_report_es_parametrizable(cartera):
    texto = cartera.report(secciones=("resumen",), tasa_libre=0.03, nivel_var=0.99)
    assert "## Composición" not in texto
    assert "99 %" in texto and "3,00 %" in texto
    with pytest.raises(ValueError):
        cartera.report(secciones=("inventada",))


def test_tablas_markdown_bien_formadas(cartera):
    for linea in cartera.report().splitlines():
        if linea.startswith("|"):
            assert linea.endswith("|")


def test_advertencias_se_activan(precios):
    from conftest import CarteraPrueba

    c = CarteraPrueba("C", precios, {"AAA": 0.9, "BBB": 0.05, "CCC": 0.05})
    texto = c.report(umbrales=UmbralesRiesgo(correlacion_alta=0.3, volatilidad_alta=0.01))
    assert "Concentración: AAA" in texto
    assert "Poca diversificación entre AAA y BBB" in texto
    assert "Volatilidad elevada" in texto


def test_avisa_de_monedas_y_cortos(precios):
    from conftest import CarteraPrueba

    class ConMonedas(CarteraPrueba):
        def obtener_monedas(self):
            return {"AAA": "USD", "BBB": "EUR", "CCC": "USD"}

    texto = ConMonedas("C", precios, {"AAA": 1.2, "BBB": -0.4, "CCC": 0.2}).report()
    assert "varias monedas" in texto and "posiciones cortas" in texto


def test_benchmark_con_beta_uno_frente_a_si_mismo(precios):
    from conftest import CarteraPrueba

    c = CarteraPrueba("C", precios[["AAA"]], {"AAA": 1.0})
    assert "Beta frente a AAA | 1,00" in c.report(benchmark=precios["AAA"])


def test_incidencias_llegan_al_informe(precios, pesos):
    from conftest import CarteraPrueba

    sucios = precios.copy()
    sucios.iloc[100, 0] = -5
    assert "<= 0" in CarteraPrueba("C", sucios, pesos).report()


def test_ruta_guarda_el_archivo(cartera, tmp_path):
    destino = tmp_path / "informe.md"
    assert cartera.report(ruta=destino) == destino.read_text(encoding="utf-8")


def test_plots_devuelve_y_guarda_todo(cartera, tmp_path, precios):
    figuras = cartera.plots_report(mostrar=False, carpeta=tmp_path, benchmark=precios["CCC"].rename("Ref"))
    assert set(figuras) == set(GRAFICOS)
    assert all(isinstance(f, Figure) for f in figuras.values())
    assert len(list(tmp_path.glob("*.png"))) == 4


def test_plots_seleccionados_y_muchos_activos(precios):
    from conftest import CarteraPrueba

    generador = np.random.default_rng(0)
    n = 12
    datos = pd.DataFrame(100 * np.exp(generador.normal(0, .01, (300, n)).cumsum(axis=0)),
                         index=pd.bdate_range("2023-01-02", periods=300),
                         columns=[f"A{i}" for i in range(n)])
    c = CarteraPrueba("Grande", datos, {f"A{i}": 1 / n for i in range(n)})
    assert set(c.plots_report(mostrar=False)) == set(GRAFICOS)
    assert "Grande" in c.report()


def test_un_solo_activo_funciona(precios):
    from conftest import CarteraPrueba

    c = CarteraPrueba("Uno", precios[["AAA"]], {"AAA": 1.0})
    assert "## Correlaciones" not in c.report()
    assert set(c.plots_report(mostrar=False)) == set(GRAFICOS)


def test_mixin_sin_implementar_avisa():
    from miax_toolkit.cartera_analisis import CarteraAnalisisMixin

    with pytest.raises(NotImplementedError):
        CarteraAnalisisMixin().report()


def test_monte_carlo_de_un_activo_y_activo_inexistente(cartera):
    r = cartera.monte_carlo(activo="AAA", n_iteraciones=10, horizonte_dias=5, semilla=1)
    assert r.nombre == "AAA"
    with pytest.raises(ErrorValidacion, match="no está"):
        cartera.monte_carlo(activo="ZZZ")


def test_plot_simulacion(cartera, tmp_path):
    destino = tmp_path / "mc.png"
    r = cartera.monte_carlo(n_iteraciones=300, horizonte_dias=30, semilla=1)
    assert isinstance(r.plot(mostrar=False, ruta=destino), Figure)
    assert destino.exists()


def test_secciones_constantes():
    assert "advertencias" in SECCIONES
