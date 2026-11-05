"""Pruebas de interoperabilidad entre extracción y cartera."""

from io import BytesIO
import json
import unittest
from unittest.mock import PropertyMock, patch

import pandas as pd

from miax_toolkit import (
    Cartera,
    SerieIndicador,
    descargar_indicador,
    descargar_serie,
    descargar_series,
)


class TestIntegracionBasica(unittest.TestCase):
    @patch("miax_toolkit.macroeconomia.urlopen")
    @patch("miax_toolkit.extractores.yf.Ticker")
    def test_contrato_comun_de_las_dos_fuentes(self, ticker, abrir):
        fechas = pd.date_range("2025-01-02", periods=3, tz="America/New_York")
        ticker.return_value.history.return_value = pd.DataFrame(
            {"Close": [90, 100, 110]}, index=fechas
        )
        ticker.return_value.get_history_metadata.return_value = {"currency": "USD"}
        abrir.return_value = BytesIO(json.dumps([
            {}, [{"date": "2024", "value": 25}, {"date": "2023", "value": 20}],
        ]).encode("utf-8"))

        precios = descargar_series(
            ["AAPL", "^GSPC"], "2025-01-01", "2025-02-01",
            tipos={"^GSPC": "indice"},
        )
        pib = descargar_indicador("ESP", "NY.GDP.MKTP.CD", 2023, 2024)

        # El mismo consumidor sirve para acciones, índices e indicadores.
        for serie in [*precios.values(), pib]:
            with self.subTest(serie=serie.valores.name):
                self.assertIsInstance(serie.valores, pd.Series)
                self.assertEqual(serie.valores.dtype, "float64")
                self.assertIsInstance(serie.valores.index, pd.DatetimeIndex)
                self.assertIsNone(serie.valores.index.tz)
                self.assertTrue(serie.valores.index.is_monotonic_increasing)
                self.assertTrue(serie.fuente)
                self.assertIn(serie.frecuencia, ("diaria", "anual"))
        self.assertEqual(precios["AAPL"].frecuencia, "diaria")
        self.assertEqual(pib.frecuencia, "anual")
        self.assertEqual(precios["AAPL"].valores.tolist(), [90.0, 100.0, 110.0])
        self.assertEqual(pib.valores.tolist(), [20.0, 25.0])
        pd.testing.assert_series_equal(precios["AAPL"].valores, precios["AAPL"].precios)

    def test_indicador_no_es_un_activo_de_cartera(self):
        pib = SerieIndicador(
            "PIB", "ESP", pd.Series(
                [20.0, 25.0], index=pd.to_datetime(["2023-12-31", "2024-12-31"])
            )
        )
        with self.assertRaisesRegex(ValueError, "SeriePrecios"):
            Cartera("Incorrecta", [pib], {"PIB": 1.0})

    @patch("miax_toolkit.extractores.yf.Ticker")
    def test_extractor_y_cartera(self, ticker):
        fechas = pd.bdate_range("2025-01-02", periods=60)
        ticker.return_value.history.return_value = pd.DataFrame(
            {"Close": [100.0 + i for i in range(60)]}, index=fechas
        )
        ticker.return_value.get_history_metadata.return_value = {"currency": "USD"}

        activos = descargar_series(
            ["AAPL", "MSFT"], "2025-01-01", "2025-05-01"
        )
        cartera = Cartera(
            "Cartera de prueba", list(activos.values()),
            {"AAPL": 0.6, "MSFT": 0.4}
        )

        self.assertEqual(list(cartera.obtener_precios()), ["AAPL", "MSFT"])
        self.assertEqual(cartera.obtener_pesos(), {"AAPL": 0.6, "MSFT": 0.4})
        self.assertEqual(cartera.obtener_monedas(), {"AAPL": "USD", "MSFT": "USD"})
        self.assertTrue(all(
            isinstance(s, pd.Series) for s in cartera.obtener_precios().values()
        ))

    @patch("miax_toolkit.extractores.yf.Ticker")
    def test_moneda_manual_tiene_prioridad(self, ticker):
        fechas = pd.bdate_range("2025-01-02", periods=60)
        ticker.return_value.history.return_value = pd.DataFrame(
            {"Close": [100.0 + i for i in range(60)]}, index=fechas
        )
        with patch.object(
            type(ticker.return_value), "fast_info", new_callable=PropertyMock, create=True
        ) as rapido:
            serie = descargar_serie("AAPL", "2025-01-01", "2025-05-01", moneda="EUR")
            self.assertEqual(serie.moneda, "EUR")
            ticker.return_value.get_history_metadata.assert_not_called()
            rapido.assert_not_called()

    @patch("miax_toolkit.extractores.yf.Ticker")
    def test_metadatos_no_disponibles(self, ticker):
        fechas = pd.bdate_range("2025-01-02", periods=60)
        ticker.return_value.history.return_value = pd.DataFrame(
            {"Close": [100.0 + i for i in range(60)]}, index=fechas
        )
        ticker.return_value.get_history_metadata.side_effect = RuntimeError("API")
        ticker.return_value.fast_info = {}
        serie = descargar_serie("AAPL", "2025-01-01", "2025-05-01")
        self.assertIsNone(serie.moneda)

    @patch("miax_toolkit.extractores.yf.Ticker")
    def test_moneda_fast_info_llega_a_cartera(self, ticker):
        fechas = pd.bdate_range("2025-01-02", periods=60)
        ticker.return_value.history.return_value = pd.DataFrame(
            {"Close": [100.0 + i for i in range(60)]}, index=fechas
        )
        ticker.return_value.get_history_metadata.return_value = {}
        ticker.return_value.fast_info = {"currency": "USD"}
        activos = descargar_series(["AAPL", "MSFT"], "2025-01-01", "2025-05-01")
        cartera = Cartera("Ejemplo", list(activos.values()), {"AAPL": 0.6, "MSFT": 0.4})
        self.assertEqual(cartera.obtener_monedas(), {"AAPL": "USD", "MSFT": "USD"})


if __name__ == "__main__":
    unittest.main()
