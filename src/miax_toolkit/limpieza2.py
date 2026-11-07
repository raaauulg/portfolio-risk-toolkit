"""Limpieza y preprocesado de series de precios."""

import numpy as np
import pandas as pd


def limpiar_precios(
    serie: pd.Series,
    nombre: str = "serie",
    max_pct_nulos: float = 0.20,
    umbral_split: float = 0.50,
):
    """Limpia una serie de precios y devuelve (serie_limpia, resumen)."""
    resumen = []  # aquí iremos apuntando todo lo que se corrige
    serie = serie.copy()  # trabajamos con una copia para no tocar el original
    n_inicial = len(serie)  # para el resumen final

    # 1. Validación y depuración de fechas
    if not isinstance(serie.index, pd.DatetimeIndex):
        original = pd.Series(serie.index.astype(str))

        # Depurar la escritura: quitar espacios y unificar separadores
        textos = original.str.strip().str.replace(r"[./]", "-", regex=True)

        # Probar los dos formatos admitidos: año-mes-día y día-mes-año
        fechas = pd.to_datetime(textos, format="%Y-%m-%d", errors="coerce")
        fechas = fechas.fillna(pd.to_datetime(textos, format="%d-%m-%Y", errors="coerce"))

        corregidas = (fechas.notna() & (original != fechas.dt.strftime("%Y-%m-%d"))).sum()
        imposibles = fechas.isna().sum()
        serie.index = pd.DatetimeIndex(fechas)

        if corregidas > 0:
            resumen.append(f"{nombre}: {corregidas} fecha(s) mal escrita(s) corregida(s).")
        if imposibles > 0:
            serie = serie[serie.index.notna()]
            resumen.append(f"{nombre}: {imposibles} fecha(s) imposible(s) eliminada(s).")

    # Quitar zona horaria y hora: así el mismo día coincide en todas las bolsas
    if serie.index.tz is not None:
        serie.index = serie.index.tz_localize(None)
    serie.index = serie.index.normalize()

    # 2. Ordenar cronológicamente
    if not serie.index.is_monotonic_increasing:
        serie = serie.sort_index()
        resumen.append(f"{nombre}: fechas desordenadas; se han ordenado.")

    # 3. Detección y tratamiento de fechas duplicadas
    duplicadas = serie.index.duplicated(keep="last").sum()
    if duplicadas > 0:
        serie = serie[~serie.index.duplicated(keep="last")]
        resumen.append(f"{nombre}: {duplicadas} fecha(s) duplicada(s); se conserva el último valor.")

    # 4. Validación de precios: numéricos y positivos
    if not pd.api.types.is_numeric_dtype(serie):
        textos = serie.astype(str).str.strip().str.replace(",", ".", regex=False)
        numeros = pd.to_numeric(textos, errors="coerce")
        no_numericos = (numeros.isna() & serie.notna()).sum()
        serie = numeros
        if no_numericos > 0:
            resumen.append(f"{nombre}: {no_numericos} precio(s) no numérico(s) convertido(s) en NA.")

    serie = serie.astype(float)
    infinitos = np.isinf(serie).sum()
    no_positivos = (serie <= 0).sum()
    serie = serie.replace([np.inf, -np.inf], np.nan).mask(serie <= 0)
    if infinitos > 0:
        resumen.append(f"{nombre}: {infinitos} precio(s) infinito(s) convertido(s) en NA.")
    if no_positivos > 0:
        resumen.append(f"{nombre}: {no_positivos} precio(s) <= 0 convertido(s) en NA.")

    # 5. Detección y tratamiento de NA
    nulos = serie.isna().sum()
    if nulos > 0:
        pct_nulos = nulos / len(serie)
        serie = serie.dropna()  # equivale a na.omit() de R
        resumen.append(f"{nombre}: {nulos} NA eliminado(s).")
        if pct_nulos > max_pct_nulos:
            resumen.append(
                f"AVISO {nombre}: el {pct_nulos:.0%} de los datos eran NA "
                f"(más del {max_pct_nulos:.0%}); revisa la fuente."
            )

    # 6. Aviso de posibles splits (no se modifica ningún dato)
    saltos = np.log(serie).diff().abs()
    fechas_salto = saltos[saltos > umbral_split].index
    for fecha in fechas_salto:
        resumen.append(
            f"AVISO {nombre}: salto muy grande el {fecha:%d/%m/%Y}; "
            "puede ser un split sin ajustar."
        )

    # 7. Resumen de la limpieza
    resumen.append(f"{nombre}: se conservan {len(serie)} de {n_inicial} observaciones.")

    return serie, resumen


def alinear_precios(precios):
    """Limpia varios activos y los pone en un calendario común.

    precios puede ser un diccionario {activo: serie} o un DataFrame con una
    columna por activo. Devuelve (tabla_alineada, resumen).
    """
    if isinstance(precios, pd.DataFrame):
        precios = {columna: precios[columna] for columna in precios.columns}

    resumen = []
    limpias = {}
    for activo, serie in precios.items():
        limpias[activo], avisos = limpiar_precios(serie, nombre=activo)
        resumen.extend(avisos)

    # Una columna por activo; donde un activo no cotiza ese día queda NA
    tabla = pd.concat(limpias, axis=1, sort=True)
    fechas_totales = len(tabla)

    # Calendario común: solo los días en que cotizan todos los activos
    tabla = tabla.dropna()

    if tabla.empty:
        raise ValueError("Los activos no tienen ninguna fecha en común.")
    descartadas = fechas_totales - len(tabla)
    if descartadas > 0:
        resumen.append(
            f"Alineación: se descartan {descartadas} de {fechas_totales} fechas "
            "por no tener precio de todos los activos."
        )
    return tabla, resumen


def validar_pesos(pesos: dict, activos) -> pd.Series:
    """Comprueba que los pesos encajan con los activos y suman 1."""
    pesos = pd.Series(pesos, dtype=float)

    faltan = sorted(set(activos) - set(pesos.index))
    sobran = sorted(set(pesos.index) - set(activos))
    if faltan or sobran:
        raise ValueError(
            f"Los pesos no coinciden con los activos. Faltan: {faltan}. Sobran: {sobran}."
        )
    if pesos.isna().any():
        raise ValueError("Hay pesos vacíos (NA).")
    if not np.isclose(pesos.sum(), 1.0):
        raise ValueError(f"Los pesos deben sumar 1 y suman {pesos.sum():.4f}.")

    return pesos.reindex(activos)  # mismo orden que las columnas de precios