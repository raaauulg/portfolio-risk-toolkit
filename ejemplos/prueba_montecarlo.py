"""Prueba del motor de Monte Carlo con t de Student."""

import matplotlib

matplotlib.use("Agg")  # guarda el gráfico en un archivo sin abrir ventanas

import numpy as np
import pandas as pd

from miax_toolkit.limpieza2 import alinear_precios
from miax_toolkit.montecarlo import simular_activo, simular_cartera

# Precios inventados de tres activos correlacionados, con semilla fija
generador = np.random.default_rng(5)
fechas = pd.bdate_range("2022-01-03", periods=750)
correlacion = np.array([[1.0, 0.6, 0.2], [0.6, 1.0, 0.3], [0.2, 0.3, 1.0]])
vol_diaria = np.array([0.020, 0.015, 0.008])
cov = np.outer(vol_diaria, vol_diaria) * correlacion
rend = generador.multivariate_normal([0.0004, 0.0003, 0.0001], cov, len(fechas))
datos = pd.DataFrame(100 * np.exp(rend.cumsum(axis=0)), index=fechas, columns=["TEC", "BANCO", "BONOS"])

precios, resumen = alinear_precios(datos)
pesos = {"TEC": 0.5, "BANCO": 0.3, "BONOS": 0.2}

# 1. Cartera con parámetros históricos
cartera = simular_cartera(precios, pesos, n_sims=10_000, horizonte=252, semilla=42)
print(cartera.interpretacion())
cartera.plot(mostrar=False, ruta="ejemplos/montecarlo_cartera.png")

# 2. Un activo, con supuestos fijados por el usuario
activo = simular_activo(precios["TEC"], retorno=0.05, volatilidad=0.30, semilla=42)
print()
print(activo.interpretacion())

# 3. Comprobación del motor: con muchas simulaciones,
#    media de ln(V_T / V0) ~ mu * T   y   desviación de ln(V_T / V0) ~ sigma * raiz(T)
mu, sigma, T = 0.08, 0.20, 1.0
prueba = simular_activo(precios["TEC"], v0=100, retorno=mu, volatilidad=sigma,
                        n_sims=100_000, horizonte=252, semilla=1)
log_final = np.log(prueba.valores_finales / 100)
print()
print(f"Media de ln(V_T/V0): {log_final.mean():.4f}   (teoría: {mu * T:.4f})")
print(f"Desviación de ln(V_T/V0): {log_final.std():.4f}   (teoría: {sigma * np.sqrt(T):.4f})")
