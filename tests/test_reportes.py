"""Pruebas de reportes.py y de los métodos report() y plots_report() de la Cartera."""

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pandas as pd
import pytest
from matplotlib.figure import Figure

from miax_toolkit import Cartera, SeriePrecios
from miax_toolkit.reportes import (
    GRAFICOS,
    SECCIONES,
    contribucion_riesgo,
    generar_plots,
    generar_report,
    metricas,
    valor_cartera,
)


@pytest.fixture
def precios():
    generador = np.random.default_rng(7)
    fechas = pd.bdate_range("2024-01-02", periods=504)
    vol = np.array([0.32, 0.24, 0.06])
    corr = np.array([[1.0, 0.85, -0.1], [0.85, 1.0, -0.05], [-0.1, -0.05, 1.0]])
    rend = generador.multivariate_normal([4e-4, 3e-4, 1e-4], np.outer(vol, vol) * corr / 252, 504)
    return pd.DataFrame(100 * np.exp(rend.cumsum(axis=0)), index=fechas, columns=["TEC", "BANCO", "BONOS"])


@pytest.fixture
def pesos():
    return {"TEC": 0.5, "BANCO": 0.3, "BONOS": 0.2}


@pytest.fixture
def cartera(precios, pesos):
    series = [SeriePrecios(a, precios[a], "sintético") for a in precios.columns]
    return Cartera("Prueba", series, pesos)


# ---------- Métricas calculadas a mano ----------

def test_valor_cartera_comprar_y_mantener():
    fechas = pd.bdate_range("2024-01-01", periods=3)
    precios = pd.DataFrame({"A": [10.0, 20.0, 20.0], "B": [10.0, 10.0, 20.0]}, index=fechas)
    valores = valor_cartera(precios, {"A": 0.5, "B": 0.5})
    # 100 * (0,5 * 20/10 + 0,5 * 20/10) = 200 al final
    assert valores.tolist() == [100.0, 150.0, 200.0]


def test_rentabilidad_anualizada_conocida():
    # Crece un 10 % anual compuesto durante dos años exactos
    valores = pd.Series(100 * 1.10 ** (np.arange(505) / 252))
    m = metricas(valores)
    assert m["rent_anual"] == pytest.approx(0.10)
    assert m["rent_total"] == pytest.approx(1.10 ** 2 - 1)


def test_caida_maxima_conocida():
    valores = pd.Series([100.0, 120.0, 90.0, 110.0])
    assert metricas(valores)["caida_maxima"] == pytest.approx(90 / 120 - 1)


def test_cvar_es_mayor_o_igual_que_var(precios):
    m = metricas(precios["TEC"])
    assert m["cvar"] >= m["var"] > 0


def test_contribucion_al_riesgo_suma_uno(precios, pesos):
    assert contribucion_riesgo(precios, pesos).sum() == pytest.approx(1.0)


def test_metricas_con_muy_pocos_datos_no_fallan():
    m = metricas(pd.Series([100.0, 101.0]))
    assert np.isnan(m["volatilidad"])


# ---------- Informe ----------

def test_informe_completo_tiene_todas_las_secciones(cartera):
    simulacion = cartera.monte_carlo(n_sims=300, horizonte=20)
    texto = cartera.report(simulacion=simulacion)
    for titulo in ("# Informe de Prueba", "## Métricas de la cartera", "## Composición",
                   "## Métricas por activo", "## Correlaciones", "## Simulación de Monte Carlo",
                   "## Diagnóstico de los datos", "## Advertencias de riesgo"):
        assert titulo in texto


def test_secciones_elegibles(cartera):
    texto = cartera.report(secciones=("resumen",))
    assert "## Métricas de la cartera" in texto
    assert "## Composición" not in texto
    assert "## Advertencias de riesgo" not in texto


def test_parametros_aparecen_en_el_informe(cartera):
    texto = cartera.report(tasa_libre=0.03, nivel_var=0.99)
    assert "tasa libre 3,00 %" in texto
    assert "al 99 %" in texto


def test_sin_simulacion_no_hay_seccion_de_monte_carlo(cartera):
    assert "## Simulación de Monte Carlo" not in cartera.report()


def test_beta_frente_a_si_mismo_es_uno(precios):
    texto = generar_report(precios[["TEC"]], {"TEC": 1.0}, benchmark=precios["TEC"].rename("TEC"))
    assert "| Beta frente a TEC | 1,00 |" in texto


def test_tablas_markdown_bien_formadas(cartera):
    for linea in cartera.report().splitlines():
        if linea.startswith("|"):
            assert linea.endswith("|")


def test_valores_invalidos_dan_error(cartera):
    with pytest.raises(ValueError, match="Secciones desconocidas"):
        cartera.report(secciones=("inventada",))
    with pytest.raises(ValueError, match="nivel_var"):
        cartera.report(nivel_var=1.5)


def test_guardar_en_archivo(cartera, tmp_path):
    destino = tmp_path / "informe.md"
    texto = cartera.report(ruta=destino)
    assert destino.read_text(encoding="utf-8") == texto


# ---------- Diagnóstico y advertencias ----------

def test_el_diagnostico_de_la_limpieza_llega_al_informe(precios, pesos):
    sucio = precios.copy()
    sucio.iloc[100, 0] = -5.0
    series = [SeriePrecios(a, sucio[a], "sintético") for a in sucio.columns]
    texto = Cartera("Sucia", series, pesos).report()
    assert "TEC: 1 precio(s) <= 0 convertido(s) en NA." in texto


def test_advertencias_de_concentracion_y_correlacion(cartera):
    texto = cartera.report()
    assert "**ALTO:** Concentración: TEC pesa un 50,0 %" in texto
    assert "Poca diversificación entre TEC y BANCO" in texto


def test_umbrales_configurables(cartera):
    texto = cartera.report(umbrales={"peso_maximo": 0.6, "correlacion_alta": 0.95})
    assert "Concentración" not in texto
    assert "Poca diversificación" not in texto


def test_aviso_de_monedas_mezcladas(precios, pesos):
    series = [SeriePrecios(a, precios[a], "sintético", moneda=m)
              for a, m in zip(precios.columns, ["USD", "EUR", "USD"])]
    assert "mezcla monedas (EUR, USD)" in Cartera("Monedas", series, pesos).report()


def test_aviso_de_historia_corta(precios, pesos):
    corta = precios.iloc[:100]
    series = [SeriePrecios(a, corta[a], "sintético") for a in corta.columns]
    assert "Historia corta" in Cartera("Corta", series, pesos).report()


def test_los_avisos_de_la_limpieza_pasan_a_advertencias(precios, pesos):
    con_split = precios.copy()
    con_split.iloc[300:, 1] /= 4
    series = [SeriePrecios(a, con_split[a], "sintético") for a in con_split.columns]
    assert "Datos: BANCO: salto muy grande" in Cartera("Split", series, pesos).report()


def test_advertencias_ordenadas_por_gravedad(cartera):
    niveles = [l.split("**")[1].rstrip(":") for l in cartera.report().splitlines() if l.startswith("- **")]
    orden = {"ALTO": 0, "MEDIO": 1, "INFO": 2}
    assert [orden[n] for n in niveles] == sorted(orden[n] for n in niveles)


# ---------- Gráficos ----------

def test_plots_report_crea_y_guarda_los_cuatro(cartera, precios, tmp_path):
    figuras = cartera.plots_report(mostrar=False, carpeta=tmp_path, benchmark=precios["BONOS"])
    assert set(figuras) == set(GRAFICOS)
    assert all(isinstance(f, Figure) for f in figuras.values())
    assert sorted(p.name for p in tmp_path.glob("*.png")) == sorted(f"{g}.png" for g in GRAFICOS)


def test_plots_elegibles(cartera):
    assert list(cartera.plots_report(graficos=("evolucion",), mostrar=False)) == ["evolucion"]


def test_grafico_desconocido_da_error(cartera):
    with pytest.raises(ValueError, match="Gráficos desconocidos"):
        cartera.plots_report(graficos=("tarta",), mostrar=False)


def test_cartera_de_un_solo_activo(precios):
    c = Cartera("Uno", [SeriePrecios("TEC", precios["TEC"], "sintético")], {"TEC": 1.0})
    assert "## Correlaciones" not in c.report()
    assert set(c.plots_report(mostrar=False)) == set(GRAFICOS)


def test_muchos_activos(precios):
    generador = np.random.default_rng(1)
    datos = pd.DataFrame(100 * np.exp(generador.normal(0, 0.01, (300, 10)).cumsum(axis=0)),
                         index=pd.bdate_range("2024-01-02", periods=300),
                         columns=[f"A{i}" for i in range(10)])
    pesos = {c: 0.1 for c in datos.columns}
    assert "Informe" in generar_report(datos, pesos)
    assert set(generar_plots(datos, pesos, mostrar=False)) == set(GRAFICOS)


def test_constantes_publicas():
    assert "advertencias" in SECCIONES and "riesgo" in GRAFICOS
