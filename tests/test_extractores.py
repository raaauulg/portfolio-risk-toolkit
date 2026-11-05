"""Pruebas del extractor con respuestas simuladas de Yahoo Finance."""

import unittest
from unittest.mock import patch

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

    def test_ticker_vacio(self):
        with self.assertRaises(ValueError):
            descargar_serie(" ", "2026-01-01", "2026-02-01")


if __name__ == "__main__":
    unittest.main()
