"""Pruebas de los adaptadores de FRED y BCE con la red simulada (apartado 4.2)."""

from unittest.mock import patch

import pandas as pd
import pytest
import requests

from miax_toolkit import SeriePrecios, SerieIndicador, descargar_sp500_fred, descargar_tipo_cambio_bce


class _Respuesta:
    """Imita lo mínimo de requests.Response que usan los adaptadores."""

    def __init__(self, texto: str):
        self.text = texto

    def raise_for_status(self) -> None:
        pass


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
    with pytest.raises(RuntimeError, match="FRED"):
        descargar_sp500_fred("2025-01-01", "2025-01-10")
