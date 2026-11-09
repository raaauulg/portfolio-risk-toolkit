"""La instantánea local se convierte en SeriePrecios con su procedencia marcada."""

import pandas as pd
import pytest

from miax_toolkit import SeriePrecios

from app.datos import recortar
from app.universos import FIN, INICIO, UNIVERSOS


def test_instantanea_produce_series_de_precios_marcadas(instantanea):
    series, metadatos = instantanea
    assert set(series) == set(metadatos.index)
    for ticker, serie in series.items():
        assert isinstance(serie, SeriePrecios)
        assert "instantánea" in serie.fuente
        assert serie.moneda == metadatos.loc[ticker, "moneda"]
        assert serie.frecuencia == "diaria"
        assert serie.precios.index.min() >= pd.Timestamp(INICIO)
        assert serie.precios.index.max() < pd.Timestamp(FIN)  # fin exclusivo
        assert serie.precios.index.is_monotonic_increasing and not serie.precios.index.has_duplicates


def test_cada_universo_tiene_una_sola_moneda(instantanea):
    series, metadatos = instantanea
    for clave, universo in UNIVERSOS.items():
        monedas = {series[t].moneda for t in metadatos.index[metadatos["universo"] == clave]}
        assert monedas == {universo.moneda}
        assert set(universo.acciones) <= set(series)


def test_recortar_crea_una_serie_nueva_con_sus_estadisticos(instantanea):
    series, _ = instantanea
    original = series["AAPL"]
    corta = recortar(original, "2024-01-01", "2025-01-01")
    assert corta.precios.index.min() >= pd.Timestamp("2024-01-01")
    assert corta.precios.index.max() < pd.Timestamp("2025-01-01")
    assert corta.media == pytest.approx(corta.precios.mean())
    assert corta.media != pytest.approx(original.media)
    assert len(original.precios) > len(corta.precios)  # el original no cambia


def test_recortar_sin_datos_da_un_error_claro(instantanea):
    series, _ = instantanea
    with pytest.raises(ValueError, match="AAPL"):
        recortar(series["AAPL"], "2025-01-04", "2025-01-06")  # fin de semana
