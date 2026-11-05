"""Estilo común de los gráficos."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

FONDO = "#fcfcfb"
COLOR_TEXTO = "#0b0b0b"
COLOR_SECUNDARIO = "#52514e"
COLOR_REJILLA = "#e6e5e1"
COLOR_ROJO = "#e34948"
COLORES = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100",
           "#e87ba4", "#008300", "#6250d6", "#e34948")
MAX_SERIES = len(COLORES)


def aplicar_estilo(eje: "Axes") -> None:
    """Deja rejilla y ejes discretos para que destaquen los datos."""
    eje.set_facecolor(FONDO)
    eje.grid(True, color=COLOR_REJILLA, linewidth=0.7)
    eje.set_axisbelow(True)
    for lado in ("top", "right"):
        eje.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        eje.spines[lado].set_color(COLOR_REJILLA)
    eje.tick_params(colors=COLOR_SECUNDARIO, labelsize=9, length=0)
    eje.xaxis.label.set_color(COLOR_SECUNDARIO)
    eje.yaxis.label.set_color(COLOR_SECUNDARIO)


def finalizar(figura: "Figure", mostrar: bool, ruta: str | Path | None) -> "Figure":
    """Guarda la figura si hay ruta y la muestra si se ha pedido."""
    if ruta is not None:
        destino = Path(ruta)
        destino.parent.mkdir(parents=True, exist_ok=True)
        figura.savefig(destino, dpi=150, facecolor=figura.get_facecolor())
    if mostrar:
        import matplotlib.pyplot as plt

        plt.show()
    return figura
