"""Comprueba que los ficheros de texto del repositorio están en UTF-8 sin BOM.

Evita que vuelva a colarse texto doblemente codificado (mojibake): la "ó"
de "integración" convertida en "A con tilde + 3 volado", que aparece al leer un fichero
UTF-8 como cp1252 y volver a guardarlo en UTF-8 (p. ej. con Windows PowerShell 5.1).
"""

from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
EXTENSIONES = {".py", ".md", ".toml", ".txt", ".cfg", ".ini"}
CARPETAS_EXCLUIDAS = {".git", ".venv", "build", "dist", "__pycache__", ".pytest_cache"}
# Secuencias típicas de UTF-8 leído como cp1252: A con tilde (vocales acentuadas),
# a con circunflejo + euro (comillas y guiones) y A con circunflejo (espacio duro).
MOJIBAKE = ("\u00c3", "\u00e2\u20ac", "\u00c2")


def _ficheros_de_texto() -> list[Path]:
    return sorted(
        ruta for ruta in RAIZ.rglob("*")
        if ruta.is_file()
        and ruta.suffix in EXTENSIONES
        and not CARPETAS_EXCLUIDAS.intersection(ruta.relative_to(RAIZ).parts)
        and not any(parte.endswith(".egg-info") for parte in ruta.parts)
    )


@pytest.mark.parametrize("ruta", _ficheros_de_texto(), ids=lambda r: r.relative_to(RAIZ).as_posix())
def test_utf8_sin_bom_ni_mojibake(ruta: Path):
    datos = ruta.read_bytes()
    assert not datos.startswith(b"\xef\xbb\xbf"), "tiene BOM"
    texto = datos.decode("utf-8")  # falla si no es UTF-8 válido
    for secuencia in MOJIBAKE:
        assert secuencia not in texto, f"posible mojibake: {secuencia!r}"
