"""Validación y limpieza de series de precios (apartado 4.5).

La regla de diseño es: se corrige lo que tiene una solución razonable y se
registra (duplicados, huecos cortos), y se rechaza con un error claro lo que
daría resultados falsos sin avisar (texto, fechas inválidas, datos no diarios,
historia demasiado corta). La justificación está en docs/validacion_inputs.md.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import pandas as pd

METODOS_ALINEACION = ("interseccion", "union")


class ErrorValidacion(ValueError):
    """Los datos de entrada no cumplen los requisitos mínimos del toolkit."""


@dataclass(frozen=True)
class ResultadoLimpieza:
    """Precios ya limpios y alineados, con el registro de lo que se ha tocado."""

    precios: pd.DataFrame
    incidencias: list[str] = field(default_factory=list)


def validar_precios(datos: pd.Series | pd.DataFrame, nombre: str = "serie") -> None:
    """Comprueba la estructura de los datos. No modifica nada.

    Lanza ErrorValidacion si no son una Series o DataFrame de pandas, si el
    índice no contiene fechas, si están vacíos o si los valores no son numéricos.
    """
    if not isinstance(datos, (pd.Series, pd.DataFrame)):
        raise ErrorValidacion(
            f"{nombre}: se esperaba una Series o DataFrame de pandas "
            f"y se ha recibido {type(datos).__name__}."
        )
    if datos.empty:
        raise ErrorValidacion(f"{nombre}: no contiene datos.")
    if not isinstance(datos.index, pd.DatetimeIndex):
        raise ErrorValidacion(
            f"{nombre}: el índice debe ser de fechas (DatetimeIndex) "
            f"y es {type(datos.index).__name__}."
        )
    if datos.index.hasnans:
        raise ErrorValidacion(f"{nombre}: el índice contiene fechas vacías.")

    columnas = datos.to_frame() if isinstance(datos, pd.Series) else datos
    for columna in columnas.columns:
        tipo = columnas[columna].dtype
        if pd.api.types.is_bool_dtype(tipo) or not pd.api.types.is_numeric_dtype(tipo):
            raise ErrorValidacion(
                f"{nombre}: la columna {columna!r} debe ser numérica y es de tipo {tipo}."
            )


def limpiar_serie(
    serie: pd.Series,
    nombre: str | None = None,
    max_relleno: int = 5,
    min_observaciones: int = 30,
    max_pct_nulos: float = 0.20,
    umbral_salto: float = 0.50,
) -> tuple[pd.Series, list[str]]:
    """Limpia una serie de precios y devuelve (serie_limpia, incidencias).

    Pasos: normaliza las fechas, ordena, elimina fechas duplicadas, convierte
    infinitos y precios <= 0 en nulos, rellena huecos con el último precio
    conocido (como máximo max_relleno días) y elimina los nulos que queden.

    Nunca se rellena hacia atrás: usar un precio futuro para tapar uno pasado
    introduciría información que aún no se conocía en esa fecha.

    Los saltos diarios mayores que umbral_salto se avisan pero no se eliminan,
    porque pueden ser reales o deberse a un split sin ajustar.
    """
    nombre = nombre or str(serie.name or "serie")
    validar_precios(serie, nombre)
    if max_relleno < 0:
        raise ValueError("max_relleno no puede ser negativo.")

    incidencias: list[str] = []
    limpia = serie.astype(float).copy()
    limpia.name = nombre

    # Quita la zona horaria conservando el día local: dos bolsas con horas de
    # cierre distintas deben coincidir en la misma fecha.
    indice = limpia.index
    if indice.tz is not None:
        indice = indice.tz_localize(None)
    limpia.index = indice.normalize()

    if not limpia.index.is_monotonic_increasing:
        limpia = limpia.sort_index()
        incidencias.append(f"{nombre}: fechas desordenadas; se han ordenado.")

    duplicadas = int(limpia.index.duplicated().sum())
    if duplicadas:
        limpia = limpia[~limpia.index.duplicated(keep="last")]
        incidencias.append(
            f"{nombre}: {duplicadas} fecha(s) duplicada(s); se conserva el último valor."
        )

    limpia = limpia.replace([np.inf, -np.inf], np.nan)
    no_positivos = int((limpia <= 0).sum())
    if no_positivos:
        limpia = limpia.mask(limpia <= 0)
        incidencias.append(
            f"{nombre}: {no_positivos} precio(s) <= 0 tratados como dato ausente."
        )

    # Los nulos iniciales solo indican que el activo aún no cotizaba.
    primer_dato = limpia.first_valid_index()
    if primer_dato is None:
        raise ErrorValidacion(f"{nombre}: no tiene ningún precio válido.")
    limpia = limpia.loc[primer_dato:]

    nulos = int(limpia.isna().sum())
    pct_nulos = nulos / len(limpia)
    if pct_nulos > max_pct_nulos:
        raise ErrorValidacion(
            f"{nombre}: {pct_nulos:.0%} de valores nulos supera el máximo "
            f"permitido ({max_pct_nulos:.0%})."
        )
    if nulos:
        rellenada = limpia.ffill(limit=max_relleno) if max_relleno else limpia
        rellenos = nulos - int(rellenada.isna().sum())
        limpia = rellenada.dropna()
        descartados = nulos - rellenos
        partes = []
        if rellenos:
            partes.append(f"{rellenos} nulo(s) rellenado(s) con el último precio")
        if descartados:
            partes.append(f"{descartados} fecha(s) sin precio descartada(s)")
        incidencias.append(f"{nombre}: " + " y ".join(partes) + ".")

    if len(limpia) < min_observaciones:
        raise ErrorValidacion(
            f"{nombre}: tiene {len(limpia)} observaciones y se necesitan "
            f"al menos {min_observaciones}."
        )

    mediana_dias = pd.Series(limpia.index).diff().dt.days.median()
    if mediana_dias > 4:
        raise ErrorValidacion(
            f"{nombre}: parece no ser diaria (mediana de {mediana_dias:.0f} días entre "
            "datos). Las métricas anualizadas de este toolkit asumen datos diarios."
        )

    saltos = int((np.log(limpia).diff().abs() > umbral_salto).sum())
    if saltos:
        incidencias.append(
            f"{nombre}: {saltos} salto(s) diario(s) muy grande(s); "
            "comprueba si hay splits sin ajustar."
        )
    return limpia, incidencias


def alinear_precios(
    datos: pd.DataFrame | Mapping[str, pd.Series],
    metodo: Literal["interseccion", "union"] = "interseccion",
    max_relleno: int = 5,
    min_observaciones: int = 30,
    max_pct_nulos: float = 0.20,
    umbral_salto: float = 0.50,
) -> ResultadoLimpieza:
    """Limpia varios activos y los pone en un calendario común.

    metodo="interseccion": conserva solo los días en que cotizan todos. No
    inventa precios, por lo que es la opción por defecto.

    metodo="union": conserva los días en que cotiza alguno y rellena los
    festivos con el último precio (hasta max_relleno días). Conserva más
    fechas, pero los días rellenados tienen rendimiento 0, lo que reduce
    ligeramente la volatilidad y la correlación medidas.

    En ambos casos solo quedan fechas posteriores al inicio del activo más
    joven, porque una cartera necesita un precio de todos sus activos.
    """
    if metodo not in METODOS_ALINEACION:
        raise ValueError(f"metodo debe ser uno de {METODOS_ALINEACION}.")
    if isinstance(datos, pd.DataFrame):
        validar_precios(datos, "precios")
        series = {str(columna): datos[columna] for columna in datos.columns}
    elif isinstance(datos, Mapping):
        series = {str(nombre): serie for nombre, serie in datos.items()}
    else:
        raise ErrorValidacion(
            "Los precios deben ser un DataFrame o un diccionario {activo: Series}."
        )
    if not series:
        raise ErrorValidacion("No se ha recibido ningún activo.")

    incidencias: list[str] = []
    relleno = max_relleno if metodo == "union" else 0
    limpias = {}
    for nombre, serie in series.items():
        limpias[nombre], avisos = limpiar_serie(
            serie,
            nombre=nombre,
            max_relleno=relleno,
            min_observaciones=min_observaciones,
            max_pct_nulos=max_pct_nulos,
            umbral_salto=umbral_salto,
        )
        incidencias.extend(avisos)

    tabla = pd.concat(limpias, axis=1, sort=True)
    if metodo == "union" and max_relleno:
        tabla = tabla.ffill(limit=max_relleno)
    filas_totales = len(tabla)
    alineada = tabla.dropna(how="any")

    if len(alineada) < min_observaciones:
        raise ErrorValidacion(
            f"Tras alinear los activos quedan {len(alineada)} fechas comunes y se "
            f"necesitan al menos {min_observaciones}."
        )
    descartadas = filas_totales - len(alineada)
    if descartadas:
        incidencias.append(
            f"Alineación ({metodo}): se descartan {descartadas} de "
            f"{filas_totales} fechas por no tener precio de todos los activos."
        )
    return ResultadoLimpieza(precios=alineada, incidencias=incidencias)


def validar_pesos(pesos: pd.Series | Mapping[str, float], activos: pd.Index) -> pd.Series:
    """Devuelve los pesos ordenados como activos o lanza ErrorValidacion."""
    serie = pd.Series(pesos, dtype=float)
    serie.index = serie.index.map(str)
    faltan = sorted(set(activos) - set(serie.index))
    sobran = sorted(set(serie.index) - set(activos))
    if faltan or sobran:
        raise ErrorValidacion(
            f"Los pesos no coinciden con los activos. Faltan: {faltan}. Sobran: {sobran}."
        )
    if not np.isfinite(serie.to_numpy()).all():
        raise ErrorValidacion("Los pesos contienen valores nulos o infinitos.")
    if not np.isclose(serie.sum(), 1.0, atol=1e-6):
        raise ErrorValidacion(f"Los pesos deben sumar 1 y suman {serie.sum():.6f}.")
    return serie.reindex(activos)
