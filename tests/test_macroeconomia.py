"""Pruebas de la API macroeconómica con respuestas simuladas."""

from io import BytesIO
import json
import unittest
from unittest.mock import patch

import pandas as pd

from miax_toolkit.macroeconomia import descargar_indicador


class TestBancoMundial(unittest.TestCase):
    @patch("miax_toolkit.macroeconomia.urlopen")
    def test_indicador_anual(self, abrir):
        cuerpo = [
            {"page": 1, "pages": 1},
            [
                {"date": "2024", "value": 25.0},
                {"date": "2023", "value": 20.0},
                {"date": "2022", "value": None},
            ],
        ]
        abrir.return_value = BytesIO(json.dumps(cuerpo).encode("utf-8"))
        datos = descargar_indicador("esp", "NY.GDP.MKTP.CD", 2022, 2024)
        self.assertEqual(datos.pais, "ESP")
        self.assertEqual(datos.fuente, "Banco Mundial")
        self.assertEqual(datos.frecuencia, "anual")
        self.assertEqual(list(datos.valores), [20.0, 25.0])
        self.assertEqual(datos.valores.index[0], pd.Timestamp("2023-12-31"))
        self.assertIn("format=json", abrir.call_args.args[0])

    @patch("miax_toolkit.macroeconomia.urlopen")
    def test_sin_datos(self, abrir):
        abrir.return_value = BytesIO(json.dumps([{}, []]).encode("utf-8"))
        with self.assertRaisesRegex(ValueError, "No hay datos"):
            descargar_indicador("ESP", "NY.GDP.MKTP.CD", 2022, 2024)

    @patch("miax_toolkit.macroeconomia.urlopen")
    def test_no_devuelve_anios_fuera_del_intervalo(self, abrir):
        abrir.return_value = BytesIO(json.dumps([{}, [
            {"date": "2019", "value": 1}, {"date": "2020", "value": 2},
            {"date": "2021", "value": 3}, {"date": "2022", "value": 4},
        ]]).encode())
        serie = descargar_indicador("ESP", "NY.GDP.MKTP.CD", 2020, 2021)
        self.assertEqual(serie.valores.tolist(), [2., 3.])

    @patch("miax_toolkit.macroeconomia.urlopen")
    def test_fila_sin_fecha_da_error_claro(self, abrir):
        abrir.return_value = BytesIO(json.dumps([{}, [{"value": 2}]]).encode())
        with self.assertRaisesRegex(ValueError, "observación anual inválida"):
            descargar_indicador("ESP", "NY.GDP.MKTP.CD", 2020, 2021)

    def test_fechas_invalidas(self):
        with self.assertRaises(ValueError):
            descargar_indicador("ESP", "NY.GDP.MKTP.CD", 2025, 2020)

    def test_codigo_invalido(self):
        with self.assertRaises(ValueError):
            descargar_indicador("../", "NY.GDP.MKTP.CD", 2020, 2025)


if __name__ == "__main__":
    unittest.main()
