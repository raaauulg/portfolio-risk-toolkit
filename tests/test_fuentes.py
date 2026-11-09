"""Pruebas de los adaptadores de FRED y BCE con la red simulada (apartado 4.2)."""

from unittest.mock import patch

import pandas as pd
import pytest
import requests

from miax_toolkit import SeriePrecios, SerieIndicador, descargar_sp500_fred, descargar_tipo_cambio_bce, descargar_indicador_fred


class _Respuesta:
    """Imita lo mínimo de requests.Response que usan los adaptadores."""

    def __init__(self, texto: str, status_code: int = 200):
        self.text = texto
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Error")


@patch("miax_toolkit.fuentes.requests.get")
def test_sp500_de_fred_es_una_serie_de_precios_como_la_de_yahoo(get):
    # FRED marca los festivos con "." en lugar de un número.
    get.return_value = _Respuesta(
        "observation_date,SP500\n2025-01-02,5868.55\n2025-01-03,5942.47\n2025-01-06,.\n2025-01-07,5909.03\n"
    )

    serie = descargar_sp500_fred("2025-01-01", "2025-01-10")

    assert isinstance(serie, SeriePrecios)
    assert serie.ticker == "^GSPC"                     # mismo identificador que en Yahoo
    assert serie.fuente == "FRED" and serie.moneda == "USD"
    assert serie.precios.tolist() == [5868.55, 5942.47, 5909.03]
    assert isinstance(serie.precios.index, pd.DatetimeIndex)


@patch("miax_toolkit.fuentes.requests.get")
def test_tipo_de_cambio_del_bce_es_un_indicador(get):
    get.return_value = _Respuesta(
        "KEY,TIME_PERIOD,OBS_VALUE\nEXR.D.USD.EUR.SP00.A,2025-01-02,1.0321\nEXR.D.USD.EUR.SP00.A,2025-01-03,1.0299\n"
    )

    serie = descargar_tipo_cambio_bce("usd", "2025-01-01", "2025-01-10")

    assert isinstance(serie, SerieIndicador)
    assert serie.fuente == "BCE" and serie.frecuencia == "diaria"
    assert serie.unidad == "USD por 1 EUR"
    assert serie.valores.tolist() == [1.0321, 1.0299]


@patch("miax_toolkit.fuentes.requests.get", side_effect=requests.ConnectionError("sin red"))
def test_fallo_de_red_da_un_error_explicito(get):
    with pytest.raises(RuntimeError, match="FRED.*conexión"):
        descargar_sp500_fred("2025-01-01", "2025-01-10")


# Respuestas reales observadas para un fin de semana (2025-01-04 a 2025-01-06):
# FRED devuelve HTTP 404 y el BCE un cuerpo vacío. No es un fallo de red.
@patch("miax_toolkit.fuentes.requests.get", return_value=_Respuesta("", status_code=404))
def test_fred_sin_observaciones_en_el_rango_da_un_error_de_datos(get):
    with pytest.raises(ValueError, match=r"FRED no tiene observaciones.*2025-01-04 y 2025-01-06"):
        descargar_sp500_fred("2025-01-04", "2025-01-06")


@patch("miax_toolkit.fuentes.requests.get", return_value=_Respuesta(""))
def test_bce_sin_observaciones_en_el_rango_da_un_error_de_datos(get):
    with pytest.raises(ValueError, match=r"BCE no tiene observaciones.*fin de semana"):
        descargar_tipo_cambio_bce("USD", "2025-01-04", "2025-01-06")


@patch("miax_toolkit.fuentes.requests.get", return_value=_Respuesta("error", status_code=503))
def test_error_del_servidor_no_se_confunde_con_falta_de_datos(get):
    with pytest.raises(RuntimeError, match="HTTP 503"):
        descargar_sp500_fred("2025-01-01", "2025-01-10")


@pytest.mark.parametrize("codigo", [429, 503])
@pytest.mark.parametrize("fuente", ["FRED", "BCE"])
@patch("miax_toolkit.fuentes.requests.get")
def test_error_http_vacio_no_se_confunde_con_falta_de_datos(get, codigo, fuente):
    get.return_value = _Respuesta("", status_code=codigo)
    with pytest.raises(RuntimeError, match=rf"{fuente}.*HTTP {codigo}"):
        if fuente == "FRED":
            descargar_sp500_fred("2025-01-01", "2025-01-10")
        else:
            descargar_tipo_cambio_bce("USD", "2025-01-01", "2025-01-10")


@patch("miax_toolkit.fuentes.requests.get")
def test_fred_indicador_conserva_unidades_y_omite_huecos(get):
    get.return_value = _Respuesta("DATE,UNRATE\n2025-01-01,4.1\n2025-02-01,.\n2025-03-01,4.2\n2025-04-01,4.3\n")
    s = descargar_indicador_fred("UNRATE", "2025-01-01", "2025-04-01", pais="USA", frecuencia="mensual", unidad="%")
    assert isinstance(s, SerieIndicador)
    assert s.valores.tolist() == [4.1, 4.2]
    assert s.frecuencia == "mensual" and s.unidad == "%"


@patch("miax_toolkit.fuentes.requests.get")
def test_csv_con_zona_horaria_se_normaliza(get):
    get.return_value = _Respuesta("TIME_PERIOD,OBS_VALUE\n2025-01-02T00:00:00+01:00,1.1\n2025-01-03T00:00:00+01:00,1.2\n")
    s = descargar_tipo_cambio_bce("USD", "2025-01-01", "2025-01-10")
    assert s.valores.index.tz is None
    assert s.valores.index[0] == pd.Timestamp("2025-01-02")
