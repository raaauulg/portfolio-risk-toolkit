"""Formato español de números, porcentajes y fechas."""

import math

import pandas as pd

from app.formato import dinero, fecha, numero, porcentaje, puntos


def test_numero_usa_punto_de_miles_y_coma_decimal():
    assert numero(1234.5) == "1.234,50"
    assert numero(-1234567.891, 1) == "-1.234.567,9"
    assert numero(0.5, 0) == "0"  # redondeo bancario de Python: 0,5 -> 0


def test_porcentajes_y_puntos():
    assert porcentaje(0.1234) == "12,3 %"
    assert porcentaje(0.1234, 2) == "12,34 %"
    assert porcentaje(0.05, signo=True) == "+5,0 %"
    assert puntos(0.013) == "+1,3 pp"
    assert puntos(-0.02) == "-2,0 pp"


def test_dinero_y_fecha():
    assert dinero(10_000, "USD") == "10.000 USD"
    assert fecha(pd.Timestamp("2025-12-31")) == "31/12/2025"


def test_valores_no_disponibles():
    for funcion in (numero, porcentaje, puntos):
        assert funcion(math.nan) == "n/d"
        assert funcion(None) == "n/d"
    assert dinero(math.inf, "EUR") == "n/d"
