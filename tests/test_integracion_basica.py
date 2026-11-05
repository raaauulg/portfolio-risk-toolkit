"""Pruebas de interoperabilidad entre extracción y cartera."""

import unittest
from unittest.mock import PropertyMock, patch

import pandas as pd

from miax_toolkit import Cartera, descargar_serie, descargar_series


class TestIntegracionBasica(unittest.TestCase):
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
