"""Herramientas para el taller B1-T1 del MIAX."""

from .cartera import Cartera
from .extractores import descargar_serie, descargar_series
from .limpieza import alinear_precios, limpiar_precios, validar_pesos
from .macroeconomia import SerieIndicador, descargar_indicador
from .modelos import SeriePrecios
from .monte_carlo import (
    SimulationResult,
    estimar_parametros,
    simular_activo,
    simular_cartera,
)

# Ordenado por capas: ingesta -> modelos -> preprocesado -> análisis.
__all__ = [
    # Ingesta
    "descargar_serie", "descargar_series", "descargar_indicador",
    # Modelos
    "SeriePrecios", "SerieIndicador", "Cartera",
    # Preprocesado
    "limpiar_precios", "alinear_precios", "validar_pesos",
    # Análisis (Monte Carlo)
    "estimar_parametros", "simular_cartera", "simular_activo", "SimulationResult",
]
