"""Pruebas del dashboard. Se omiten si no está instalado el extra [app] (streamlit y plotly)."""

from importlib.util import find_spec

import pytest

if find_spec("streamlit") is None or find_spec("plotly") is None:
    collect_ignore_glob = ["test_*.py"]
else:
    import matplotlib

    matplotlib.use("Agg")  # backend sin ventana: los tests no abren gráficos

    @pytest.fixture(scope="session", autouse=True)
    def cerrar_temporal_apptest():
        """Cierra el temporal global de AppTest 1.66.1 al terminar las pruebas."""
        from streamlit.testing.v1 import app_test

        yield
        app_test.TMP_DIR.cleanup()


@pytest.fixture(scope="session")
def instantanea():
    from app.datos import leer_instantanea

    return leer_instantanea()


@pytest.fixture(scope="session")
def calcular_preset(instantanea):
    """Devuelve una función que calcula un preset con la instantánea, sin Streamlit."""
    from app.analisis import calcular
    from app.configuracion import PRESETS
    from app.datos import recortar

    series, _ = instantanea
    memoria = {}

    def _calcular(clave: str):
        if clave not in memoria:
            c = PRESETS[clave].config
            activos = {a: recortar(series[a], c.inicio, c.fin) for a in c.activos}
            referencia = recortar(series[c.benchmark], c.inicio, c.fin) if c.benchmark else None
            memoria[clave] = calcular(c, activos, referencia)
        return memoria[clave]

    return _calcular
