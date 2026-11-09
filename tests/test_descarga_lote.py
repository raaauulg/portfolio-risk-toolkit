"""Pruebas sin conexión de la descarga en lote."""

import unittest
from unittest.mock import patch

from miax_toolkit.extractores import descargar_series


class TestDescargaLote(unittest.TestCase):
    @patch("miax_toolkit.extractores.descargar_serie")
    def test_varios_activos(self, descarga):
        descarga.side_effect = ["serie_1", "serie_2", "serie_3"]
        resultado = descargar_series(
            ["aapl", "msft", "^GSPC"],
            "2025-01-01", "2026-01-01",
            tipos={"^GSPC": "indice"},
            monedas={"AAPL": "USD", "MSFT": "USD"},
        )
        self.assertEqual(list(resultado), ["AAPL", "MSFT", "^GSPC"])
        self.assertEqual(descarga.call_count, 3)
        self.assertEqual(descarga.call_args_list[2].kwargs["tipo_activo"], "indice")
        self.assertEqual(descarga.call_args_list[0].kwargs["moneda"], "USD")

    def test_lista_vacia(self):
        with self.assertRaises(ValueError):
            descargar_series([], "2025-01-01", "2026-01-01")

    def test_duplicados(self):
        with self.assertRaises(ValueError):
            descargar_series(["AAPL", "aapl"], "2025-01-01", "2026-01-01")

    @patch("miax_toolkit.extractores.descargar_serie")
    def test_metadatos_con_ticker_erroneo_no_se_ignoran(self, descarga):
        with self.assertRaisesRegex(ValueError, "tickers del lote"):
            descargar_series(["AAPL"], "2025-01-01", "2026-01-01", monedas={"aapl": "EUR"})
        descarga.assert_not_called()

    @patch("miax_toolkit.extractores.descargar_serie")
    def test_error_no_se_silencia(self, descarga):
        descarga.side_effect = RuntimeError("API no disponible")
        with self.assertRaises(RuntimeError):
            descargar_series(["AAPL"], "2025-01-01", "2026-01-01")


if __name__ == "__main__":
    unittest.main()
