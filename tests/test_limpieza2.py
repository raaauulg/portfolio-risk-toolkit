"""Pruebas automáticas de limpieza2: limpiar_precios, alinear_precios y validar_pesos.

Ejecutar desde la carpeta principal del proyecto:
    python -m pytest tests/test_limpieza2.py -v
"""

import numpy as np
import pandas as pd
import pytest

from miax_toolkit.limpieza2 import alinear_precios, limpiar_precios, validar_pesos


def serie_normal(n=40, inicio="2024-01-01"):
    """Serie sin problemas: n días de mercado con precios de 100 a 120."""
    return pd.Series(np.linspace(100, 120, n), index=pd.bdate_range(inicio, periods=n))


def contiene(resumen, texto):
    return any(texto in linea for linea in resumen)


# ---------- 1. Fechas ----------

def test_fechas_mal_escritas_se_corrigen():
    s = pd.Series([10, 11, 12, 13], index=["2024-01-02", " 03/01/2024", "04.01.2024", "2024/01/05"])
    limpia, resumen = limpiar_precios(s)
    esperadas = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"])
    assert list(limpia.index) == list(esperadas)
    assert contiene(resumen, "3 fecha(s) mal escrita(s) corregida(s)")


def test_formato_iso_no_se_confunde_con_dia_mes():
    # 2024-01-02 es el 2 de enero, no el 1 de febrero
    limpia, _ = limpiar_precios(pd.Series([10, 11], index=["2024-01-02", "2024-01-03"]))
    assert limpia.index[0] == pd.Timestamp("2024-01-02")


def test_fechas_imposibles_se_eliminan():
    s = pd.Series([10, 11, 12], index=["2024-01-02", "hola", "2024-13-45"])
    limpia, resumen = limpiar_precios(s)
    assert len(limpia) == 1
    assert contiene(resumen, "2 fecha(s) imposible(s) eliminada(s)")


def test_zona_horaria_y_hora_se_quitan():
    s = serie_normal()
    s.index = s.index.tz_localize("America/New_York") + pd.Timedelta(hours=16)
    limpia, _ = limpiar_precios(s)
    assert limpia.index.tz is None
    assert (limpia.index == limpia.index.normalize()).all()


# ---------- 2 y 3. Orden y duplicados ----------

def test_fechas_desordenadas_se_ordenan():
    s = pd.Series([12, 10, 11], index=["2024-01-04", "2024-01-02", "2024-01-03"])
    limpia, resumen = limpiar_precios(s)
    assert limpia.tolist() == [10, 11, 12]
    assert contiene(resumen, "se han ordenado")


def test_fecha_duplicada_conserva_el_ultimo_valor():
    s = pd.Series([10, 11, 15, 12], index=["2024-01-02", "2024-01-03", "2024-01-03", "2024-01-04"])
    limpia, resumen = limpiar_precios(s)
    assert len(limpia) == 3
    assert limpia[pd.Timestamp("2024-01-03")] == 15
    assert contiene(resumen, "1 fecha(s) duplicada(s)")


# ---------- 4. Precios numéricos y positivos ----------

def test_texto_con_coma_decimal_se_convierte():
    s = pd.Series([10, " 11,5", "12"], index=["2024-01-02", "2024-01-03", "2024-01-04"])
    limpia, _ = limpiar_precios(s)
    assert limpia.tolist() == [10.0, 11.5, 12.0]


def test_texto_no_numerico_se_elimina():
    s = pd.Series([10, "abc", 12], index=["2024-01-02", "2024-01-03", "2024-01-04"])
    limpia, resumen = limpiar_precios(s)
    assert limpia.tolist() == [10.0, 12.0]
    assert contiene(resumen, "1 precio(s) no numérico(s)")


def test_precios_cero_negativos_e_infinitos_se_eliminan():
    s = serie_normal(10)
    s.iloc[2], s.iloc[4], s.iloc[6] = 0, -5, np.inf
    limpia, resumen = limpiar_precios(s)
    assert len(limpia) == 7
    assert (limpia > 0).all() and np.isfinite(limpia).all()
    assert contiene(resumen, "2 precio(s) <= 0")
    assert contiene(resumen, "1 precio(s) infinito(s)")


# ---------- 5. NA ----------

def test_na_se_eliminan_sin_rellenar():
    s = serie_normal(10)
    s.iloc[[3, 4]] = np.nan
    limpia, resumen = limpiar_precios(s)
    assert len(limpia) == 8
    assert s.index[3] not in limpia.index  # no hay ffill ni bfill
    assert contiene(resumen, "2 NA eliminado(s)")


def test_aviso_si_mas_del_20_por_ciento_son_na():
    s = serie_normal(20)
    s.iloc[:5] = np.nan  # 25 %
    _, resumen = limpiar_precios(s)
    assert contiene(resumen, "AVISO")
    assert contiene(resumen, "25%")


def test_sin_aviso_si_hay_pocos_na():
    s = serie_normal(20)
    s.iloc[3] = np.nan  # 5 %
    _, resumen = limpiar_precios(s)
    assert not contiene(resumen, "AVISO")


def test_el_umbral_de_na_se_puede_cambiar():
    s = serie_normal(20)
    s.iloc[3] = np.nan  # 5 %
    _, resumen = limpiar_precios(s, max_pct_nulos=0.01)
    assert contiene(resumen, "AVISO")


# ---------- 6. Splits ----------

def test_aviso_de_split_sin_tocar_los_datos():
    s = serie_normal(40)
    s.iloc[20:] = s.iloc[20:] / 4  # caída del 75 % en un día
    limpia, resumen = limpiar_precios(s)
    pd.testing.assert_series_equal(limpia, s, check_freq=False, check_names=False)
    assert contiene(resumen, f"salto muy grande el {s.index[20]:%d/%m/%Y}")


def test_sin_aviso_de_split_en_una_serie_normal():
    _, resumen = limpiar_precios(serie_normal())
    assert not contiene(resumen, "split")


# ---------- 7. Resumen y decisiones de diseño ----------

def test_resumen_final():
    s = serie_normal(10)
    s.iloc[2] = np.nan
    _, resumen = limpiar_precios(s, nombre="AAPL")
    assert resumen[-1] == "AAPL: se conservan 9 de 10 observaciones."


def test_serie_limpia_no_genera_incidencias():
    _, resumen = limpiar_precios(serie_normal())
    assert len(resumen) == 1  # solo la línea final del resumen


def test_no_modifica_la_serie_original():
    s = serie_normal(10)
    s.iloc[2] = -1
    copia = s.copy()
    limpiar_precios(s)
    pd.testing.assert_series_equal(s, copia)


def test_series_cortas_y_no_diarias_se_admiten():
    # Decisión del grupo: no se exige longitud mínima ni frecuencia diaria
    corta = pd.Series([1.0, 2.0, 3.0], index=pd.bdate_range("2024-01-01", periods=3))
    mensual = pd.Series(np.arange(1.0, 13), index=pd.date_range("2024-01-31", periods=12, freq="ME"))
    assert len(limpiar_precios(corta)[0]) == 3
    assert len(limpiar_precios(mensual)[0]) == 12


# ---------- Alineación de varios activos ----------

def test_calendario_comun_con_festivos_distintos():
    fechas = pd.bdate_range("2024-01-01", periods=40)
    a = pd.Series(np.linspace(10, 20, 40), index=fechas)
    b = pd.Series(np.linspace(30, 40, 40), index=fechas).drop(fechas[[5, 15]])
    tabla, resumen = alinear_precios({"A": a, "B": b})
    assert tabla.shape == (38, 2)
    assert not tabla.isna().any().any()
    assert contiene(resumen, "se descartan 2 de 40 fechas")


def test_activos_de_distintas_bolsas_coinciden_en_el_mismo_dia():
    fechas = pd.bdate_range("2024-01-01", periods=40)
    nueva_york = pd.Series(np.linspace(10, 20, 40),
                           index=fechas.tz_localize("America/New_York") + pd.Timedelta(hours=16))
    madrid = pd.Series(np.linspace(30, 40, 40),
                       index=fechas.tz_localize("Europe/Madrid") + pd.Timedelta(hours=17, minutes=30))
    tabla, _ = alinear_precios({"NY": nueva_york, "MAD": madrid})
    assert len(tabla) == 40


def test_activo_mas_joven_marca_el_inicio():
    viejo = serie_normal(60, "2024-01-01")
    joven = serie_normal(40, "2024-02-01")
    tabla, _ = alinear_precios({"VIEJO": viejo, "JOVEN": joven})
    assert tabla.index[0] == joven.index[0]


def test_dataframe_y_diccionario_dan_lo_mismo():
    datos = {"A": serie_normal(), "B": serie_normal() * 2}
    tabla_dict, _ = alinear_precios(datos)
    tabla_df, _ = alinear_precios(pd.DataFrame(datos))
    pd.testing.assert_frame_equal(tabla_dict, tabla_df)


def test_resumen_incluye_los_avisos_de_cada_activo():
    a = serie_normal()
    b = serie_normal()
    b.iloc[3] = -1
    _, resumen = alinear_precios({"A": a, "B": b})
    assert contiene(resumen, "B: 1 precio(s) <= 0")


def test_sin_fechas_comunes_da_error():
    a = serie_normal(10, "2023-01-02")
    b = serie_normal(10, "2025-01-01")
    with pytest.raises(ValueError, match="ninguna fecha en común"):
        alinear_precios({"A": a, "B": b})


# ---------- Validación de pesos ----------

def test_pesos_correctos_se_ordenan_como_los_activos():
    pesos = validar_pesos({"B": 0.4, "A": 0.6}, ["A", "B"])
    assert pesos.tolist() == [0.6, 0.4]


@pytest.mark.parametrize("pesos, mensaje", [
    ({"A": 0.6, "B": 0.6}, "suman"),
    ({"A": 1.0}, "Faltan"),
    ({"A": 0.5, "B": 0.3, "C": 0.2}, "Sobran"),
    ({"A": np.nan, "B": 1.0}, "vacíos"),
])
def test_pesos_incorrectos_dan_error(pesos, mensaje):
    with pytest.raises(ValueError, match=mensaje):
        validar_pesos(pesos, ["A", "B"])


def test_pesos_con_decimales_que_suman_uno():
    pesos = validar_pesos({"A": 0.1, "B": 0.2, "C": 0.7}, ["A", "B", "C"])
    assert pesos.sum() == pytest.approx(1.0)
