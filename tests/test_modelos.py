"""Pruebas de SeriePrecios, SerieIndicador y Cartera con datos sintéticos."""

import unittest

import numpy as np
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

    def test_precios_complejos_se_rechazan_sin_descartar_la_parte_imaginaria(self):
        datos = pd.Series([90+1j, 100+2j], index=pd.date_range("2025-01-01", periods=2))
        with self.assertRaisesRegex(ValueError, "reales"):
            SeriePrecios("AAA", datos, "ejemplo")

    def test_indicador_normaliza_zona_horaria_y_rechaza_nulos(self):
        from miax_toolkit import SerieIndicador
        fechas = pd.date_range("2025-01-01", periods=2, tz="Europe/Madrid")
        serie = SerieIndicador("I", "ESP", pd.Series([1., 2.], index=fechas))
        self.assertIsNone(serie.valores.index.tz)
        self.assertEqual(serie.valores.index[0], pd.Timestamp("2025-01-01"))
        with self.assertRaisesRegex(ValueError, "finitos"):
            SerieIndicador("I", "ESP", pd.Series([1., np.nan], index=fechas))

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
