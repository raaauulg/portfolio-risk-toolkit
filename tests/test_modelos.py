"""Pruebas básicas de las DataClasses con datos sintéticos."""

import unittest

import pandas as pd

from miax_toolkit.cartera import Cartera
from miax_toolkit.modelos import SeriePrecios


class TestModelos(unittest.TestCase):
    def setUp(self):
        fechas = pd.date_range("2026-01-01", periods=3)
        self.serie = SeriePrecios("AAA", pd.Series([90, 100, 110], index=fechas), "ejemplo")

    def test_estadisticos_automaticos(self):
        self.assertEqual(self.serie.media, 100.0)
        self.assertEqual(self.serie.desviacion_tipica, 10.0)

    def test_fecha_obligatoria(self):
        with self.assertRaises(ValueError):
            SeriePrecios("AAA", pd.Series([90, 100, 110]), "ejemplo")

    def test_cartera_valida(self):
        cartera = Cartera("Mi cartera", [self.serie], {"AAA": 1.0})
        self.assertEqual(cartera.obtener_pesos(), {"AAA": 1.0})
        self.assertEqual(cartera.obtener_precios()["AAA"].iloc[-1], 110.0)

    def test_pesos_invalidos(self):
        with self.assertRaises(ValueError):
            Cartera("Mi cartera", [self.serie], {"AAA": 0.5})

    def test_ticker_sin_peso(self):
        with self.assertRaises(ValueError):
            Cartera("Mi cartera", [self.serie], {"BBB": 1.0})

    def test_tickers_duplicados(self):
        with self.assertRaises(ValueError):
            Cartera("Mi cartera", [self.serie, self.serie], {"AAA": 1.0})


if __name__ == "__main__":
    unittest.main()
