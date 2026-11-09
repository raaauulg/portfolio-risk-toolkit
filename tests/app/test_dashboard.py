"""La app completa con streamlit.testing.v1.AppTest, sin navegador y sin Internet."""

from datetime import date
import socket
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
import requests
import streamlit as st
from streamlit.testing.v1 import AppTest

DASHBOARD = str(Path(__file__).resolve().parents[2] / "app" / "dashboard.py")
PAGINAS = ["paginas/datos_calidad.py", "paginas/cartera_riesgo.py", "paginas/monte_carlo.py",
           "paginas/informe.py", "paginas/arquitectura.py"]


@pytest.fixture(autouse=True)
def cachés_limpias():
    st.cache_data.clear()
    st.cache_resource.clear()
    yield


def _app(preset: str | None = None) -> AppTest:
    app = AppTest.from_file(DASHBOARD, default_timeout=60)
    if preset:
        app.query_params["preset"] = preset
    return app.run()


def _sin_errores(app: AppTest) -> None:
    assert not app.exception, [e.value for e in app.exception]
    assert not app.main.error, [e.value for e in app.main.error]


def _textos(elementos) -> str:
    return " ".join(e.value for e in elementos)


def test_arranca_sin_conexion_con_el_estado_vacio():
    app = _app()
    _sin_errores(app)
    assert "Elige un preset" in _textos(app.main.info)
    assert app.radio(key="w_modo").value == "instantanea"  # modo por defecto: sin conexión


@pytest.mark.parametrize("via", ["url", "boton"])
def test_preset_demo_deja_todas_las_paginas_listas(via):
    if via == "url":
        app = _app("demo")
    else:
        app = _app()
        app.button(key="preset_demo").click().run()
    _sin_errores(app)
    assert len(app.metric) == 6  # tarjetas KPI del Resumen
    assert "cambios sin aplicar" not in _textos(app.sidebar.info)
    assert st.session_state is not None
    for pagina in PAGINAS:
        app.switch_page(pagina).run()
        _sin_errores(app)
        assert "Elige un preset" not in _textos(app.main.info), pagina


def test_pesos_invalidos_muestran_el_aviso_del_toolkit():
    app = _app("demo")
    app.number_input(key="w_peso_AAPL").set_value(50.0).run()
    assert "deben sumar 100 %" in _textos(app.sidebar.warning)
    app.button(key="calcular").click().run()
    assert not app.exception
    assert "Los pesos de la cartera deben sumar 1." in _textos(app.main.warning)
    assert "Elige un preset" in _textos(app.main.info)  # la página no se rompe: vuelve al estado vacío


def test_mezclar_monedas_muestra_el_aviso_del_toolkit():
    app = _app()
    app.multiselect(key="w_activos").set_value(["AAPL", "SAN.MC"]).run()
    app.selectbox(key="w_benchmark").set_value("ninguno").run()
    app.button(key="calcular").click()
    app.number_input(key="w_peso_AAPL").set_value(50.0)
    app.number_input(key="w_peso_SAN.MC").set_value(50.0)
    app.run()
    app.button(key="calcular").click().run()
    assert not app.exception
    assert "mezcla monedas" in _textos(app.main.warning)


def _calcular_en_directo(benchmark: str = "ninguno") -> AppTest:
    """Modo En directo con AAPL y MSFT al 50 %; las descargas las simula cada test."""
    app = _app()
    app.radio(key="w_modo").set_value("directo").run()
    app.text_input(key="w_tickers").set_value("AAPL, MSFT").run()
    app.selectbox(key="w_benchmark").set_value(benchmark)
    app.number_input(key="w_peso_AAPL").set_value(50.0)
    app.number_input(key="w_peso_MSFT").set_value(50.0)
    app.run()
    return app.button(key="calcular").click().run()


class _Respuesta:
    """Lo mínimo de requests.Response que usa el adaptador de FRED."""

    def __init__(self, texto: str, status_code: int = 200):
        self.text, self.status_code = texto, status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Error")


def _yahoo_responde(ticker) -> None:
    fechas = pd.bdate_range("2025-01-02", periods=60)
    ticker.return_value.history.return_value = pd.DataFrame({"Close": np.linspace(100, 110, 60)}, index=fechas)
    ticker.return_value.get_history_metadata.return_value = {"currency": "USD"}


@patch("miax_toolkit.extractores.yf.Ticker")
def test_fallo_de_red_en_yahoo_muestra_un_mensaje_amable(ticker):
    ticker.return_value.history.side_effect = ConnectionError("sin red")  # toolkit -> RuntimeError
    app = _calcular_en_directo()
    assert not app.exception
    mensaje = _textos(app.main.error)
    assert "No se pudieron descargar los datos" in mensaje and "Instantánea" in mensaje
    assert not app.main.warning


@patch("miax_toolkit.fuentes.requests.get", side_effect=requests.ConnectionError("sin red"))
@patch("miax_toolkit.extractores.yf.Ticker")
def test_fallo_de_red_en_fred_es_un_error_de_conexion(ticker, get):
    _yahoo_responde(ticker)
    app = _calcular_en_directo(benchmark="^GSPC")  # el S&P 500 se descarga de FRED
    assert not app.exception
    mensaje = _textos(app.main.error)
    assert "fallo de conexión" in mensaje and "No se pudo conectar con FRED" in mensaje
    assert "Instantánea" in mensaje
    assert not app.main.warning  # no se confunde con «no hay datos»


@patch("miax_toolkit.fuentes.requests.get", return_value=_Respuesta("error", status_code=503))
@patch("miax_toolkit.extractores.yf.Ticker")
def test_error_del_servidor_de_fred_es_un_error_de_conexion(ticker, get):
    _yahoo_responde(ticker)
    app = _calcular_en_directo(benchmark="^GSPC")
    assert not app.exception
    assert "HTTP 503" in _textos(app.main.error)
    assert not app.main.warning


@patch("miax_toolkit.fuentes.requests.get", return_value=_Respuesta("", status_code=404))
@patch("miax_toolkit.extractores.yf.Ticker")
def test_fred_sin_observaciones_es_un_aviso_de_datos_no_de_red(ticker, get):
    _yahoo_responde(ticker)  # FRED responde 404 cuando el rango no tiene observaciones
    app = _calcular_en_directo(benchmark="^GSPC")
    assert not app.exception
    aviso = _textos(app.main.warning)
    assert "No hay datos para esa consulta" in aviso and "FRED no tiene observaciones" in aviso
    assert "No es un fallo de conexión" in aviso
    assert not app.main.error


@patch("miax_toolkit.extractores.yf.Ticker")
def test_yahoo_sin_precios_es_un_aviso_de_datos(ticker):
    ticker.return_value.history.return_value = pd.DataFrame()  # ticker inexistente o rango vacío
    app = _calcular_en_directo()
    assert not app.exception
    aviso = _textos(app.main.warning)
    assert "No hay datos para esa consulta" in aviso and "no devolvió precios" in aviso
    assert "ticker inexistente" in aviso
    assert not app.main.error


def test_rango_sin_sesiones_en_la_instantanea_es_un_aviso_de_datos():
    app = _app("demo")
    app.date_input(key="w_desde").set_value(date(2025, 1, 4))
    app.date_input(key="w_hasta").set_value(date(2025, 1, 5))  # sábado y domingo
    app.run()
    app.button(key="calcular").click().run()
    assert not app.exception
    assert "No hay datos para esa consulta" in _textos(app.main.warning)
    assert not app.main.error


def test_la_demo_no_necesita_red(monkeypatch):
    original = socket.socket.connect

    def solo_local(self, direccion, *args, **kwargs):
        if isinstance(direccion, tuple) and direccion[0] not in ("127.0.0.1", "::1", "localhost"):
            raise OSError(f"Conexión bloqueada en el test: {direccion}")
        return original(self, direccion, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", solo_local)
    app = _app("demo")
    _sin_errores(app)
    for pagina in PAGINAS:
        app.switch_page(pagina).run()
        _sin_errores(app)
