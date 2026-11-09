"""Pruebas del extractor con respuestas simuladas de Yahoo Finance."""

import unittest
from types import MappingProxyType
from unittest.mock import PropertyMock, patch

import pandas as pd

from miax_toolkit.extractores import descargar_serie


class TestExtractorYahoo(unittest.TestCase):
    def setUp(self):
        self.fechas = pd.date_range("2026-01-05", periods=3, tz="America/New_York")
        self.datos = pd.DataFrame({"Close": [90.0, 100.0, 110.0]}, index=self.fechas)

    @patch("miax_toolkit.extractores.yf.Ticker")
    def test_accion(self, ticker_mock):
        ticker_mock.return_value.history.return_value = self.datos
        serie = descargar_serie("aapl", "2026-01-01", "2026-02-01")
        self.assertEqual(serie.ticker, "AAPL")
        self.assertEqual(serie.fuente, "Yahoo Finance")
        self.assertEqual(serie.media, 100.0)
        self.assertIsNone(serie.precios.index.tz)
        ticker_mock.return_value.history.assert_called_once_with(
            start="2026-01-01", end="2026-02-01", interval="1d", auto_adjust=True
        )

    @patch("miax_toolkit.extractores.yf.Ticker")
    def test_indice(self, ticker_mock):
        ticker_mock.return_value.history.return_value = self.datos
        serie = descargar_serie("^GSPC", "2026-01-01", "2026-02-01", tipo_activo="indice")
        self.assertEqual(serie.tipo_activo, "indice")
        self.assertEqual(serie.ticker, "^GSPC")

    @patch("miax_toolkit.extractores.yf.Ticker")
    def test_sin_datos(self, ticker_mock):
        ticker_mock.return_value.history.return_value = pd.DataFrame()
        with self.assertRaisesRegex(ValueError, "no devolvió"):
            descargar_serie("INVALID", "2026-01-01", "2026-02-01")

    @patch("miax_toolkit.extractores.yf.Ticker")
    def test_fallo_api(self, ticker_mock):
        ticker_mock.return_value.history.side_effect = ConnectionError("fallo")
        with self.assertRaisesRegex(RuntimeError, "No se pudo descargar"):
            descargar_serie("AAPL", "2026-01-01", "2026-02-01")

    def test_fechas_invalidas(self):
        with self.assertRaises(ValueError):
            descargar_serie("AAPL", "2026-02-01", "2026-01-01")

    @patch("miax_toolkit.extractores.yf.Ticker")
    def test_recorta_el_intervalo_inclusivo_exclusivo(self, ticker_mock):
        ticker_mock.return_value.history.return_value = self.datos
        serie = descargar_serie("AAPL", "2026-01-05", "2026-01-07", moneda="USD")
        self.assertEqual(serie.precios.tolist(), [90., 100.])

    @patch("miax_toolkit.extractores.yf.Ticker")
    def test_formato_compacto_se_rechaza_antes_de_consultar(self, ticker_mock):
        with self.assertRaisesRegex(ValueError, "AAAA-MM-DD"):
            descargar_serie("AAPL", "20260101", "20260201")
        ticker_mock.assert_not_called()

    def test_ticker_vacio(self):
        with self.assertRaises(ValueError):
            descargar_serie(" ", "2026-01-01", "2026-02-01")

    @patch("miax_toolkit.extractores.yf.Ticker")
    def test_moneda_metadatos_dict_o_mapping(self, ticker_mock):
        instrumento = ticker_mock.return_value
        instrumento.history.return_value = self.datos
        casos = ({"currency": " usd "}, MappingProxyType({"currency": " usd "}))
        for metadatos in casos:
            with self.subTest(tipo=type(metadatos).__name__):
                instrumento.get_history_metadata.return_value = metadatos
                with patch.object(
                    type(instrumento), "fast_info", new_callable=PropertyMock, create=True
                ) as rapido:
                    serie = descargar_serie("AAPL", "2026-01-01", "2026-02-01")
                    self.assertEqual(serie.moneda, "USD")
                    rapido.assert_not_called()

    @patch("miax_toolkit.extractores.yf.Ticker")
    def test_moneda_fast_info_sin_moneda_en_metadatos(self, ticker_mock):
        instrumento = ticker_mock.return_value
        instrumento.history.return_value = self.datos
        instrumento.fast_info = {"currency": " usd "}
        casos = (None, "invalido", {}, {"currency": None}, {"currency": " "}, {"currency": 1})
        for metadatos in casos:
            with self.subTest(metadatos=metadatos):
                instrumento.get_history_metadata.return_value = metadatos
                serie = descargar_serie("AAPL", "2026-01-01", "2026-02-01")
                self.assertEqual(serie.moneda, "USD")

    @patch("miax_toolkit.extractores.yf.Ticker")
    def test_moneda_fast_info_si_metadatos_fallan(self, ticker_mock):
        instrumento = ticker_mock.return_value
        instrumento.history.return_value = self.datos
        instrumento.get_history_metadata.side_effect = ConnectionError("metadatos")
        instrumento.fast_info = {"currency": "USD"}
        serie = descargar_serie("AAPL", "2026-01-01", "2026-02-01")
        self.assertEqual(serie.moneda, "USD")

    @patch("miax_toolkit.extractores.yf.Ticker")
    def test_moneda_desconocida_si_fast_info_falla(self, ticker_mock):
        instrumento = ticker_mock.return_value
        instrumento.history.return_value = self.datos
        instrumento.get_history_metadata.side_effect = ConnectionError("metadatos")
        with patch.object(
            type(instrumento), "fast_info", new_callable=PropertyMock, create=True
        ) as rapido:
            rapido.side_effect = ConnectionError("fast_info")
            serie = descargar_serie("AAPL", "2026-01-01", "2026-02-01")
        self.assertIsNone(serie.moneda)
        esperados = self.datos["Close"].copy()
        esperados.index = esperados.index.tz_localize(None)
        esperados.name = "AAPL"
        pd.testing.assert_series_equal(serie.precios, esperados)

    @patch("miax_toolkit.extractores.yf.Ticker")
    def test_moneda_desconocida_si_fast_info_no_es_valido(self, ticker_mock):
        instrumento = ticker_mock.return_value
        instrumento.history.return_value = self.datos
        instrumento.get_history_metadata.return_value = {}
        casos = (None, {}, {"currency": None}, {"currency": ""}, {"currency": " "}, {"currency": 1})
        for rapido in casos:
            with self.subTest(fast_info=rapido):
                instrumento.fast_info = rapido
                serie = descargar_serie("AAPL", "2026-01-01", "2026-02-01")
                self.assertIsNone(serie.moneda)


if __name__ == "__main__":
    unittest.main()
