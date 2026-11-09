"""Paleta, tipografía y plantilla de gráficos en un solo sitio.

Paleta categórica validada para daltonismo (comprobación CVD entre pares
adyacentes: ΔE ≥ 9,1 en claro y 8,4 en oscuro). Coincide al hex con
reportes.COLORES del toolkit, así que las figuras de matplotlib del núcleo y las
de Plotly del dashboard comparten colores. Los colores se asignan siempre en el
mismo orden y nunca se reciclan (como máximo, 8 activos).
"""

import plotly.graph_objects as go

FUENTE = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'

TOKENS = {
    "claro": {
        "series": ("#2a78d6", "#eb6834", "#1baf7a", "#eda100",
                   "#e87ba4", "#008300", "#6250d6", "#e34948"),
        "texto": "#0b0b0b", "texto_secundario": "#52514e", "acento": "#1c5cab",
        "rejilla": "#e1e0d9", "eje": "#c3c2b7", "fondo": "#ffffff",
        "cartera": "#0b0b0b", "referencia": "#52514e",
        "banda_exterior": "rgba(42,120,214,0.16)", "banda_interior": "rgba(42,120,214,0.32)",
        "trayectoria": "rgba(42,120,214,0.16)",
        "divergente": ((0.0, "#256abf"), (0.5, "#f0efec"), (1.0, "#e34948")),
        "alto": "#b42318", "medio": "#8a5a00", "bueno": "#006300",
    },
    "oscuro": {
        "series": ("#3987e5", "#d95926", "#199e70", "#c98500",
                   "#d55181", "#008300", "#9085e9", "#e66767"),
        "texto": "#f0efec", "texto_secundario": "#c3c2b7", "acento": "#6da7ec",
        "rejilla": "#2c2c2a", "eje": "#383835", "fondo": "#141413",
        "cartera": "#f0efec", "referencia": "#c3c2b7",
        "banda_exterior": "rgba(57,135,229,0.20)", "banda_interior": "rgba(57,135,229,0.38)",
        "trayectoria": "rgba(57,135,229,0.20)",
        "divergente": ((0.0, "#3987e5"), (0.5, "#383835"), (1.0, "#e66767")),
        "alto": "#e66767", "medio": "#fab219", "bueno": "#0ca30c",
    },
}


def tokens(modo: str = "claro") -> dict:
    return TOKENS["oscuro" if modo == "oscuro" else "claro"]


def colores_activos(activos, modo: str = "claro") -> dict[str, str]:
    """Color fijo por activo según su posición en la cartera (el color sigue al activo)."""
    serie = tokens(modo)["series"]
    activos = list(activos)
    if len(activos) > len(serie):
        raise ValueError(f"Como máximo {len(serie)} activos: los colores no se reciclan.")
    return dict(zip(activos, serie))


def aplicar(figura: go.Figure, titulo: str, eje_x: str | None, eje_y: str | None,
            modo: str = "claro", alto: int = 380, leyenda: bool = True) -> go.Figure:
    """Plantilla común: título, ejes con unidades, formato español y colores del tema."""
    t = tokens(modo)
    figura.update_layout(
        title=dict(text=titulo, x=0, xanchor="left", font=dict(size=16, color=t["texto"])),
        font=dict(family=FUENTE, size=13, color=t["texto"]),
        separators=",.",                           # decimal «,» y miles «.»
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=alto, margin=dict(l=10, r=10, t=70 if leyenda else 50, b=10),
        showlegend=leyenda,
        legend=dict(orientation="h", x=0, xanchor="left", y=1.0, yanchor="bottom",
                    bgcolor="rgba(0,0,0,0)", font=dict(size=12)),
        hoverlabel=dict(font=dict(family=FUENTE, size=13)),
    )
    ejes = dict(gridcolor=t["rejilla"], linecolor=t["eje"], zerolinecolor=t["eje"],
                tickfont=dict(color=t["texto_secundario"]), title_font=dict(color=t["texto_secundario"]),
                automargin=True)
    figura.update_xaxes(title_text=eje_x, **ejes)
    figura.update_yaxes(title_text=eje_y, **ejes)
    return figura


CSS = """
<style>
[data-testid="stMetricValue"] { font-variant-numeric: tabular-nums; }
[data-testid="stMetricLabel"] p { font-size: 0.95rem; }
.block-container { padding-top: 3.2rem; }
</style>
"""
