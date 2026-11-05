"""Datos sintéticos y una Cartera mínima para probar sin depender de internet."""

from dataclasses import dataclass, field

import matplotlib
import numpy as np
import pandas as pd
import pytest

matplotlib.use("Agg")

from miax_toolkit.cartera_analisis import CarteraAnalisisMixin  # noqa: E402


def generar_precios(n=750, semilla=1):
    generador = np.random.default_rng(semilla)
    fechas = pd.bdate_range("2022-01-03", periods=n)
    medias = np.array([0.0005, 0.0003, 0.0001])
    covarianza = np.array([[4, 2, 0.2], [2, 3, 0.1], [0.2, 0.1, 1]]) * 1e-4
    rendimientos = generador.multivariate_normal(medias, covarianza, n)
    return pd.DataFrame(100 * np.exp(rendimientos.cumsum(axis=0)), index=fechas,
                        columns=["AAA", "BBB", "CCC"])


@dataclass
class CarteraPrueba(CarteraAnalisisMixin):
    nombre: str
    precios: pd.DataFrame
    pesos: dict = field(default_factory=dict)

    def obtener_precios(self):
        return self.precios

    def obtener_pesos(self):
        return self.pesos


@pytest.fixture
def precios():
    return generar_precios()


@pytest.fixture
def pesos():
    return {"AAA": 0.5, "BBB": 0.3, "CCC": 0.2}


@pytest.fixture
def cartera(precios, pesos):
    return CarteraPrueba("Prueba", precios, pesos)
