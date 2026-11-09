"""Página 6 · Arquitectura: diagramas y desacoplamiento. No necesita resultados."""

import ast
from pathlib import Path

import streamlit as st

from app import textos

RAIZ = Path(__file__).resolve().parents[2]
DOCS = RAIZ / "docs"


def api_usada() -> list[str]:
    """Nombres de miax_toolkit que importa el código de app/, leídos de sus imports con ast."""
    nombres = set()
    for fichero in (RAIZ / "app").rglob("*.py"):
        for nodo in ast.walk(ast.parse(fichero.read_text(encoding="utf-8"))):
            if isinstance(nodo, ast.ImportFrom) and (nodo.module or "").startswith("miax_toolkit"):
                nombres |= {f"{nodo.module}.{alias.name}" for alias in nodo.names}
    return sorted(nombres)


st.title("Arquitectura")
for frase in textos.ARQUITECTURA:
    st.markdown(f"- {frase}")

uml, flujo = st.tabs(["Clases y dependencias (UML)", "Del dato al informe (secuencia)"])
with uml:
    st.image(str(DOCS / "arquitectura.svg"), width=900)
with flujo:
    secuencia = DOCS / "secuencia.svg"  # generado con mermaid-cli desde docs/arquitectura.md
    if secuencia.exists():
        st.image(str(secuencia), width="stretch")
    else:
        st.markdown("1. `descargar_series()` → `SeriePrecios` (valida y calcula media y desviación)\n"
                    "2. `Cartera(nombre, series, pesos)` → valida pesos\n"
                    "3. `monte_carlo()` → limpieza y alineación → `simular_cartera()` → `SimulationResult`\n"
                    "4. `report()` / `plots_report()` → Markdown y figuras\n"
                    "5. **Dashboard** → lee esos resultados y los pinta")

st.subheader("API pública que usa el dashboard")
st.caption("Lista generada a partir de los imports de app/. Un test comprueba que ningún nombre "
           "es privado (prefijo «_»).")
st.code("\n".join(api_usada()), language="text")
