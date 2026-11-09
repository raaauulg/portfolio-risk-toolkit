"""El dashboard es un consumidor más: solo usa la API pública y el núcleo no depende de él."""

import ast
from pathlib import Path
import subprocess
import sys

RAIZ = Path(__file__).resolve().parents[2]


def _imports(carpeta: Path):
    for fichero in carpeta.rglob("*.py"):
        for nodo in ast.walk(ast.parse(fichero.read_text(encoding="utf-8"))):
            if isinstance(nodo, ast.ImportFrom) and nodo.module:
                yield fichero, nodo.module, [a.name for a in nodo.names]
            elif isinstance(nodo, ast.Import):
                for alias in nodo.names:
                    yield fichero, alias.name, []


def test_app_solo_usa_nombres_publicos_del_toolkit():
    usados = 0
    for fichero, modulo, nombres in _imports(RAIZ / "app"):
        if modulo.startswith("miax_toolkit"):
            usados += 1
            privados = [p for p in modulo.split(".") + nombres if p.startswith("_")]
            assert not privados, f"{fichero.name} importa partes internas: {privados}"
    assert usados > 0


def test_el_nucleo_no_importa_la_capa_de_presentacion():
    for fichero, modulo, _ in _imports(RAIZ / "src"):
        assert modulo.split(".")[0] not in {"streamlit", "plotly", "app"}, fichero


def test_importar_el_toolkit_no_carga_streamlit_ni_plotly():
    codigo = ("import miax_toolkit, sys; "
              "assert 'streamlit' not in sys.modules and 'plotly' not in sys.modules")
    subprocess.run([sys.executable, "-c", codigo], check=True, cwd=RAIZ)
