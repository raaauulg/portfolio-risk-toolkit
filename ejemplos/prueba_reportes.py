"""Prueba de report() y plots_report() con precios inventados (no necesita internet).

Ejecutar desde la carpeta principal del proyecto:
    python ejemplos/prueba_reportes.py
"""

import matplotlib

matplotlib.use("Agg")  # guarda los gráficos en archivos sin abrir ventanas

import numpy as np
import pandas as pd

from miax_toolkit import Cartera, SeriePrecios

# Cuatro activos inventados y correlacionados, dos años de datos, con semilla fija
generador = np.random.default_rng(7)
fechas = pd.bdate_range("2024-01-02", periods=504)
nombres = ["TEC", "BANCO", "ENERGIA", "BONOS"]
vol_anual = np.array([0.32, 0.24, 0.22, 0.06])
correlacion = np.array([[1.00, 0.85, 0.30, -0.10],
                        [0.85, 1.00, 0.40, -0.05],
                        [0.30, 0.40, 1.00, 0.00],
                        [-0.10, -0.05, 0.00, 1.00]])
cov = np.outer(vol_anual, vol_anual) * correlacion / 252
rend = generador.multivariate_normal(np.array([0.10, 0.07, 0.05, 0.03]) / 252, cov, len(fechas))
precios = 100 * np.exp(rend.cumsum(axis=0))

series = [SeriePrecios(n, pd.Series(precios[:, i], index=fechas), "sintético", moneda="EUR")
          for i, n in enumerate(nombres)]
# Problemas a propósito, para que aparezcan en el diagnóstico
series[1].precios.iloc[[50, 51]] = np.nan          # dos días sin precio
series[2].precios.iloc[300] = -1.0                 # un precio imposible

cartera = Cartera("Cartera demo", series, {"TEC": 0.45, "BANCO": 0.25, "ENERGIA": 0.20, "BONOS": 0.10})
indice = pd.Series(np.exp(np.log(precios[:, :2]).mean(axis=1)), index=fechas, name="Índice")

# 1. Informe completo, con Monte Carlo y referencia
simulacion = cartera.monte_carlo(n_sims=5000, horizonte=252)
informe = cartera.report(tasa_libre=0.02, benchmark=indice, simulacion=simulacion,
                         ruta="ejemplos/informe_cartera.md")
print(informe)

# 2. Informe parametrizado: solo dos secciones y límites más estrictos
print(cartera.report(secciones=("resumen", "advertencias"), nivel_var=0.99,
                     umbrales={"peso_maximo": 0.30}))

# 3. Gráficos, guardados en ejemplos/graficos
cartera.plots_report(benchmark=indice, mostrar=False, carpeta="ejemplos/graficos")
print("Gráficos guardados en ejemplos/graficos")
