"""Pruebas de limpieza, alineación y validación de pesos (apartado 4.5)."""

import numpy as np
import pandas as pd
import pytest

from miax_toolkit import alinear_precios, limpiar_precios, validar_pesos


def test_limpiar_precios_quita_invalidos_sin_tocar_el_original():
    fechas = pd.to_datetime(["2025-01-03", "2025-01-02", "2025-01-06", "2025-01-06", "2025-01-07", "2025-01-08"])
    original = pd.Series([101.0, 100.0, np.nan, 103.0, -5.0, np.inf], index=fechas)
    copia = original.copy()

    limpia, resumen = limpiar_precios(original, nombre="AAA")

    assert limpia.index.is_monotonic_increasing          # se ordena
    assert not limpia.index.has_duplicates               # duplicado: se queda el último
    assert limpia.tolist() == [100.0, 101.0, 103.0]       # sin NaN, negativos ni infinitos
    assert resumen
    pd.testing.assert_series_equal(original, copia)      # el original no cambia


def test_alinear_precios_deja_solo_fechas_comunes():
    habiles = pd.bdate_range("2025-01-01", periods=20)
    sin_lunes = habiles[habiles.day_of_week != 0]
    precios = {
        "AAA": pd.Series(np.linspace(100, 110, len(habiles)), index=habiles),
        "BBB": pd.Series(np.linspace(50, 55, len(sin_lunes)), index=sin_lunes),
    }

    tabla, resumen = alinear_precios(precios)

    assert tabla.index.equals(sin_lunes)                 # festivos de una bolsa: no se rellenan
    assert list(tabla.columns) == ["AAA", "BBB"]
    assert any("Alineación" in linea for linea in resumen)


def test_sin_fechas_comunes_da_error():
    precios = {
        "AAA": pd.Series([1.0, 2.0], index=pd.to_datetime(["2025-01-02", "2025-01-03"])),
        "BBB": pd.Series([1.0, 2.0], index=pd.to_datetime(["2025-02-03", "2025-02-04"])),
    }
    with pytest.raises(ValueError):
        alinear_precios(precios)


def test_validar_pesos_ordena_y_rechaza_incoherencias():
    assert validar_pesos({"B": 0.4, "A": 0.6}, ["A", "B"]).tolist() == [0.6, 0.4]

    with pytest.raises(ValueError, match="sumar 1"):
        validar_pesos({"A": 0.6, "B": 0.6}, ["A", "B"])
    with pytest.raises(ValueError, match="no coinciden"):
        validar_pesos({"A": 1.0}, ["A", "B"])


def test_no_convierte_intradia_en_cierres_sin_avisar():
    fechas = pd.to_datetime(["2025-01-02 10:00", "2025-01-02 16:00", "2025-01-03 16:00"])
    with pytest.raises(ValueError, match="intradía"):
        limpiar_precios(pd.Series([100., 101., 102.], index=fechas))


def test_duplicados_conservan_el_ultimo_en_el_orden_original():
    fechas = pd.to_datetime(["2025-01-03", "2025-01-02", "2025-01-03", "2025-01-02"])
    limpia, _ = limpiar_precios(pd.Series([100., 90., 103., 95.], index=fechas))
    assert limpia.tolist() == [95., 103.]


@pytest.mark.parametrize("valores", [[True, 100, 101], [1+2j, 100, 101]])
def test_booleanos_y_complejos_no_se_convierten_en_precios(valores):
    with pytest.raises(ValueError, match="reales"):
        limpiar_precios(pd.Series(valores, index=pd.bdate_range("2025-01-01", periods=3)))


@pytest.mark.parametrize("opciones", [{"max_pct_nulos": np.nan}, {"max_pct_nulos": 2}, {"umbral_split": -1}])
def test_umbrales_de_limpieza_invalidos(opciones):
    with pytest.raises(ValueError):
        limpiar_precios(pd.Series([100., 101., 102.], index=pd.bdate_range("2025-01-01", periods=3)), **opciones)


def test_pesos_redondeados_se_normalizan_sin_admitir_desvios_mayores():
    pesos = validar_pesos({"A": .333333, "B": .333333, "C": .3333335}, ["A", "B", "C"])
    assert pesos.sum() == pytest.approx(1., abs=1e-15)
    with pytest.raises(ValueError, match="sumar 1"):
        validar_pesos({"A": .9}, ["A"])
