import numpy as np
import pandas as pd
import pytest

from miax_toolkit.limpieza import (
    ErrorValidacion,
    alinear_precios,
    limpiar_serie,
    validar_pesos,
    validar_precios,
)


def serie(n=60, inicio="2024-01-01"):
    return pd.Series(np.linspace(100, 120, n), index=pd.bdate_range(inicio, periods=n), name="X")


@pytest.mark.parametrize(
    "dato",
    [[1, 2, 3],
     pd.Series([1.0, 2.0]),
     pd.Series(dtype=float, index=pd.DatetimeIndex([])),
     pd.Series(["a", "b"], index=pd.bdate_range("2024-01-01", periods=2)),
     pd.Series([True, False], index=pd.bdate_range("2024-01-01", periods=2))],
)
def test_rechaza_estructuras_invalidas(dato):
    with pytest.raises(ErrorValidacion):
        validar_precios(dato)


def test_ordena_y_quita_duplicados():
    datos = serie()
    desordenada = pd.concat([datos.iloc[::-1], datos.iloc[[0]] * 2])
    limpia, incidencias = limpiar_serie(desordenada)
    assert limpia.index.is_monotonic_increasing and limpia.index.is_unique
    assert len(limpia) == len(datos)
    assert len(incidencias) == 2


def test_rellena_solo_hacia_delante_y_hasta_el_limite():
    datos = serie()
    datos.iloc[10:18] = np.nan  # hueco de 8 días
    limpia, _ = limpiar_serie(datos, max_relleno=5)
    assert limpia.iloc[10:15].eq(datos.iloc[9]).all()
    assert len(limpia) == len(datos) - 3
    assert limpia.index[15] == datos.index[18]


def test_precios_no_positivos_e_infinitos_son_nulos():
    datos = serie()
    datos.iloc[5] = -1
    datos.iloc[6] = 0
    datos.iloc[7] = np.inf
    limpia, incidencias = limpiar_serie(datos)
    assert (limpia > 0).all() and np.isfinite(limpia).all()
    assert any("<= 0" in texto for texto in incidencias)


def test_quita_nulos_iniciales_sin_contarlos():
    datos = serie(100)
    datos.iloc[:40] = np.nan
    limpia, incidencias = limpiar_serie(datos)
    assert len(limpia) == 60 and not incidencias


def test_zona_horaria_coincide_con_serie_sin_zona():
    fechas = pd.bdate_range("2024-01-01", periods=60)
    con_zona = pd.Series(np.arange(1.0, 61), index=fechas.tz_localize("America/New_York") + pd.Timedelta(hours=16))
    sin_zona = pd.Series(np.arange(1.0, 61), index=fechas)
    resultado = alinear_precios({"A": con_zona, "B": sin_zona})
    assert len(resultado.precios) == 60


def test_rechaza_poca_historia_muchos_nulos_y_datos_no_diarios():
    with pytest.raises(ErrorValidacion, match="observaciones"):
        limpiar_serie(serie(10))
    nulos = serie(100)
    nulos.iloc[1::2] = np.nan
    with pytest.raises(ErrorValidacion, match="nulos"):
        limpiar_serie(nulos)
    mensual = pd.Series(np.arange(1.0, 41), index=pd.date_range("2020-01-31", periods=40, freq="ME"))
    with pytest.raises(ErrorValidacion, match="diaria"):
        limpiar_serie(mensual)


def test_avisa_de_saltos_sin_eliminarlos():
    datos = serie()
    datos.iloc[30:] = datos.iloc[30:] / 4
    limpia, incidencias = limpiar_serie(datos)
    assert len(limpia) == len(datos)
    assert any("split" in texto for texto in incidencias)


def calendarios():
    fechas = pd.bdate_range("2024-01-01", periods=60)
    a = pd.Series(np.linspace(10, 20, 60), index=fechas)
    b = pd.Series(np.linspace(30, 40, 60), index=fechas).drop(fechas[[10, 20]])
    return {"A": a, "B": b}


def test_interseccion_no_inventa_precios():
    resultado = alinear_precios(calendarios(), metodo="interseccion")
    assert len(resultado.precios) == 58
    assert not resultado.precios.isna().any().any()


def test_union_rellena_festivos():
    resultado = alinear_precios(calendarios(), metodo="union")
    assert len(resultado.precios) == 60
    assert resultado.precios["B"].iloc[10] == resultado.precios["B"].iloc[9]


def test_dataframe_y_diccionario_dan_lo_mismo():
    datos = calendarios()
    tabla = pd.concat(datos, axis=1)
    pd.testing.assert_frame_equal(alinear_precios(tabla).precios, alinear_precios(datos).precios)


def test_activo_joven_recorta_y_sin_solape_falla():
    fechas = pd.bdate_range("2024-01-01", periods=60)
    antiguo = pd.Series(np.arange(1.0, 61), index=fechas)
    joven = pd.Series(np.arange(1.0, 61), index=pd.bdate_range("2024-02-01", periods=60))
    assert alinear_precios({"A": antiguo, "B": joven}, min_observaciones=20).precios.index[0] == joven.index[0]
    with pytest.raises(ErrorValidacion, match="fechas comunes"):
        alinear_precios({"A": antiguo, "B": joven}, min_observaciones=50)


def test_incidencia_cuando_se_descartan_fechas():
    assert any("descartan" in texto for texto in alinear_precios(calendarios()).incidencias)


def test_pesos():
    activos = pd.Index(["A", "B"])
    assert validar_pesos({"B": 0.4, "A": 0.6}, activos).tolist() == [0.6, 0.4]
    with pytest.raises(ErrorValidacion, match="suman"):
        validar_pesos({"A": 0.6, "B": 0.6}, activos)
    with pytest.raises(ErrorValidacion, match="Faltan"):
        validar_pesos({"A": 1.0}, activos)
    with pytest.raises(ErrorValidacion, match="nulos"):
        validar_pesos({"A": float("nan"), "B": 1.0}, activos)
