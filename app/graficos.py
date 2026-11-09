"""Figuras interactivas de Plotly a partir de resultados ya calculados por el toolkit.

Funciones puras: reciben series o tablas y devuelven go.Figure, sin Streamlit. No
calculan métricas; como mucho agrupan en intervalos para dibujar un histograma.
Porcentajes en el eje como 0-100 con sufijo « %», fechas dd/mm/aaaa y separadores
españoles (plantilla en estilo.aplicar).
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from app import estilo
from app.formato import porcentaje

_FECHA = "%{x|%d/%m/%Y}"
_EJE_FECHAS = dict(tickformat="%m/%Y", hoverformat="%d/%m/%Y")  # meses en número: sin depender del idioma


def evolucion(valores: pd.Series, valores_ref: pd.Series | None = None, nombre: str = "Cartera",
              nombre_ref: str | None = None, modo: str = "claro") -> go.Figure:
    """Valor de la cartera frente al benchmark, ambos en base 100."""
    t = estilo.tokens(modo)
    figura = go.Figure()
    if valores_ref is not None:
        figura.add_trace(go.Scatter(
            x=valores_ref.index, y=valores_ref, name=nombre_ref or "Referencia",
            line=dict(color=t["referencia"], width=1.8, dash="dash"),
            hovertemplate=f"{_FECHA}<br>%{{y:,.1f}}<extra>{nombre_ref}</extra>"))
    figura.add_trace(go.Scatter(
        x=valores.index, y=valores, name=nombre, line=dict(color=t["cartera"], width=2.5),
        hovertemplate=f"{_FECHA}<br>%{{y:,.1f}}<extra>{nombre}</extra>"))
    figura.add_hline(y=100, line=dict(color=t["eje"], width=1))
    figura.update_xaxes(**_EJE_FECHAS)
    titulo = f"Evolución de {nombre}" + (f" frente a {nombre_ref}" if nombre_ref else "")
    return estilo.aplicar(figura, titulo + " (base 100)", "Fecha", "Valor (base 100)", modo, alto=420)


def precios_base100(tabla: pd.DataFrame, modo: str = "claro") -> go.Figure:
    """Una línea por activo, todas en base 100 el primer día."""
    colores = estilo.colores_activos(tabla.columns, modo)
    figura = go.Figure()
    for activo in tabla.columns:
        figura.add_trace(go.Scatter(
            x=tabla.index, y=tabla[activo], name=activo, line=dict(color=colores[activo], width=2),
            hovertemplate=f"{_FECHA}<br>%{{y:,.1f}}<extra>{activo}</extra>"))
    figura.add_hline(y=100, line=dict(color=estilo.tokens(modo)["eje"], width=1))
    figura.update_xaxes(**_EJE_FECHAS)
    return estilo.aplicar(figura, "Precios normalizados (base 100 el primer día común)",
                          "Fecha", "Precio (base 100)", modo, alto=420)


def composicion(pesos: pd.Series, modo: str = "claro") -> go.Figure:
    """Pesos de la cartera, de mayor a menor, con la etiqueta escrita en cada barra."""
    colores = estilo.colores_activos(pesos.index, modo)
    orden = pesos.sort_values()
    figura = go.Figure(go.Bar(
        x=orden * 100, y=orden.index, orientation="h", marker_color=[colores[a] for a in orden.index],
        text=[porcentaje(p) for p in orden], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}: %{x:,.1f} %<extra></extra>", name="Peso"))
    figura.update_xaxes(ticksuffix=" %", range=[0, orden.max() * 100 * 1.2])  # hueco para la etiqueta
    return estilo.aplicar(figura, "Composición de la cartera", "Peso inicial (%)", None, modo,
                          alto=320, leyenda=False)


def peso_vs_riesgo(pesos: pd.Series, riesgo: pd.Series, modo: str = "claro") -> go.Figure:
    """Peso inicial frente a aportación al riesgo; la segunda serie lleva trama rayada."""
    t = estilo.tokens(modo)
    orden = riesgo.sort_values().index
    trama = dict(shape="/", fillmode="overlay", fgcolor=t["fondo"], fgopacity=0.6, solidity=0.25)
    figura = go.Figure([
        go.Bar(y=orden, x=pesos[orden] * 100, name="Peso", orientation="h", marker_color=t["series"][0],
               hovertemplate="%{y} · peso: %{x:,.1f} %<extra></extra>"),
        go.Bar(y=orden, x=riesgo[orden] * 100, name="Aportación al riesgo", orientation="h",
               marker=dict(color=t["series"][1], pattern=trama),
               hovertemplate="%{y} · aportación al riesgo: %{x:,.1f} %<extra></extra>"),
    ])
    figura.update_layout(barmode="group", bargap=0.25)
    figura.update_xaxes(ticksuffix=" %", rangemode="tozero")
    return estilo.aplicar(figura, "Peso frente a aportación al riesgo (pesos iniciales fijos)",
                          "% del total", None, modo, alto=320)


def correlacion(matriz: pd.DataFrame, modo: str = "claro") -> go.Figure:
    """Matriz de correlación con escala divergente fija de -1 a 1 y el valor escrito en cada celda."""
    t = estilo.tokens(modo)
    texto = [[f"{v:.2f}".replace(".", ",") for v in fila] for fila in matriz.to_numpy()]
    figura = go.Figure(go.Heatmap(
        z=matriz.to_numpy(), x=list(matriz.columns), y=list(matriz.index), zmin=-1, zmax=1,
        colorscale=[list(p) for p in t["divergente"]], text=texto, texttemplate="%{text}",
        textfont=dict(size=13), hovertemplate="%{y} · %{x}: %{z:.2f}<extra></extra>",
        colorbar=dict(title=dict(text="ρ"), tickvals=[-1, -0.5, 0, 0.5, 1]), xgap=2, ygap=2))
    figura.update_yaxes(autorange="reversed")
    lado = 140 + 52 * len(matriz)
    return estilo.aplicar(figura, "Correlación de rendimientos logarítmicos diarios (la que usa Monte Carlo)",
                          None, None, modo, alto=max(340, min(lado, 560)), leyenda=False)


def caidas(serie: pd.Series, nombre: str = "Cartera", modo: str = "claro") -> go.Figure:
    """Drawdown: caída desde el máximo previo, en %, con la caída máxima señalada."""
    t = estilo.tokens(modo)
    color = t["series"][7]
    figura = go.Figure(go.Scatter(
        x=serie.index, y=serie * 100, name="Caída desde máximos", fill="tozeroy",
        line=dict(color=color, width=1.5), fillcolor=color + "40",  # mismo color al 25 % de opacidad
        hovertemplate=f"{_FECHA}<br>%{{y:,.1f}} %<extra></extra>"))
    peor = serie.idxmin()
    figura.add_annotation(x=peor, y=serie.min() * 100, text=f"Máxima: {porcentaje(serie.min())}",
                          showarrow=True, arrowhead=0, ax=40, ay=20, font=dict(color=t["texto"]))
    figura.update_yaxes(ticksuffix=" %")
    figura.update_xaxes(**_EJE_FECHAS)
    return estilo.aplicar(figura, f"Caídas desde máximos (drawdown) de {nombre}", "Fecha",
                          "Caída desde el máximo previo (%)", modo, alto=340, leyenda=False)


def volatilidad_movil(serie: pd.Series, ventana: int, modo: str = "claro") -> go.Figure:
    """Volatilidad anualizada en una ventana móvil de sesiones."""
    t = estilo.tokens(modo)
    figura = go.Figure(go.Scatter(
        x=serie.index, y=serie * 100, name=f"Volatilidad móvil ({ventana} sesiones)",
        line=dict(color=t["series"][0], width=2),
        hovertemplate=f"{_FECHA}<br>%{{y:,.1f}} % anual<extra></extra>"))
    figura.update_yaxes(ticksuffix=" %", rangemode="tozero")
    figura.update_xaxes(**_EJE_FECHAS)
    return estilo.aplicar(figura, f"Volatilidad móvil anualizada ({ventana} sesiones)", "Fecha",
                          "Volatilidad anualizada (%)", modo, alto=340, leyenda=False)


def distribucion_rendimientos(rendimientos: pd.Series, var: float, cvar: float, nivel: float,
                              modo: str = "claro") -> go.Figure:
    """Histograma de rendimientos diarios con las líneas de VaR y CVaR que calcula el toolkit."""
    t = estilo.tokens(modo)
    figura = go.Figure(go.Histogram(
        x=rendimientos * 100, nbinsx=80, name="Días", marker_color=t["series"][0],
        marker_line=dict(color=t["fondo"], width=1),
        hovertemplate="Rendimiento %{x} %<br>%{y} días<extra></extra>"))
    nivel_txt = porcentaje(nivel, 0)
    # El CVaR siempre queda a la izquierda del VaR: cada etiqueta hacia su lado para que no se pisen.
    for valor, etiqueta, guion, lado in ((var, f"VaR {nivel_txt}: {porcentaje(-var)}", "dash", "top right"),
                                         (cvar, f"CVaR {nivel_txt}: {porcentaje(-cvar)}", "dot", "top left")):
        if np.isfinite(valor):
            figura.add_vline(x=-valor * 100, line=dict(color=t["alto"], width=2, dash=guion),
                             annotation=dict(text=etiqueta, font=dict(color=t["texto"]), yanchor="top",
                                             bgcolor=t["fondo"]),
                             annotation_position=lado)
    figura.update_xaxes(ticksuffix=" %")
    return estilo.aplicar(figura, "Distribución de rentabilidades diarias de la cartera",
                          "Rentabilidad diaria (%)", "Número de días", modo, alto=340, leyenda=False)


def abanico(percentiles: pd.DataFrame, muestras: np.ndarray, v0: float, moneda: str,
            modo: str = "claro") -> go.Figure:
    """Abanico de percentiles P5-P95 y P25-P75, mediana, trayectorias de muestra y valor inicial."""
    t = estilo.tokens(modo)
    dias = np.arange(len(percentiles))
    figura = go.Figure()
    for i, fila in enumerate(muestras):
        figura.add_trace(go.Scatter(x=dias, y=fila, mode="lines", line=dict(color=t["trayectoria"], width=1),
                                    hoverinfo="skip", showlegend=i == 0, legendgroup="muestra",
                                    name=f"{len(muestras)} trayectorias"))
    for bajo, alto, color, nombre in (("P5", "P95", t["banda_exterior"], "Entre P5 y P95"),
                                      ("P25", "P75", t["banda_interior"], "Entre P25 y P75")):
        figura.add_trace(go.Scatter(x=dias, y=percentiles[alto], mode="lines", line=dict(width=0),
                                    hoverinfo="skip", showlegend=False, legendgroup=nombre))
        figura.add_trace(go.Scatter(x=dias, y=percentiles[bajo], mode="lines", line=dict(width=0),
                                    fill="tonexty", fillcolor=color, name=nombre, legendgroup=nombre,
                                    hoverinfo="skip"))
    for columna, guion in (("P5", "dash"), ("P50", "solid"), ("P95", "dash")):
        figura.add_trace(go.Scatter(
            x=dias, y=percentiles[columna], mode="lines", name="Mediana (P50)" if columna == "P50" else columna,
            line=dict(color=t["series"][0], width=2.5 if columna == "P50" else 1.2, dash=guion),
            showlegend=columna == "P50",
            hovertemplate=f"Día %{{x}}<br>{columna}: %{{y:,.0f}} {moneda}<extra></extra>"))
    figura.add_hline(y=v0, line=dict(color=t["referencia"], width=1.5, dash="dot"),
                     annotation=dict(text="Valor inicial", font=dict(color=t["texto_secundario"])),
                     annotation_position="bottom left")
    figura.update_xaxes(range=[0, dias[-1]])
    figura.update_yaxes(tickformat=",.0f")  # 10.000 en lugar de 10k
    estilo.aplicar(figura, "Escenarios simulados: abanico de percentiles", "Días de mercado",
                   f"Valor de la cartera ({moneda})", modo, alto=470)
    # Cinco entradas no caben en una línea a 1366 px: leyenda bajo el eje para no pisar el título.
    figura.update_layout(legend=dict(y=-0.22, yanchor="top"), margin=dict(t=50, b=10))
    return figura


def histograma_final(finales: np.ndarray, resumen: dict, limites: tuple[float, float], moneda: str,
                     modo: str = "claro") -> go.Figure:
    """Distribución del valor final (entre P1 y P99) con P5, P50, P95 y el valor inicial."""
    t = estilo.tokens(modo)
    bajo, alto = limites
    visibles = finales[(finales >= bajo) & (finales <= alto)]
    figura = go.Figure(go.Histogram(
        x=visibles, nbinsx=50, marker_color=t["series"][0], marker_line=dict(color=t["fondo"], width=1),
        name="Escenarios", hovertemplate=f"%{{x}} {moneda}<br>%{{y}} escenarios<extra></extra>"))
    lineas = (("P5", resumen["P5"], "dash"), ("P50", resumen["P50"], "solid"),
              ("P95", resumen["P95"], "dash"), ("Inicial", resumen["valor_inicial"], "dot"))
    for i, (nombre, valor, guion) in enumerate(lineas):
        color = t["referencia"] if nombre == "Inicial" else t["texto"]
        figura.add_vline(x=valor, line=dict(color=color, width=1.8, dash=guion),
                         annotation=dict(text=nombre, font=dict(color=t["texto"], size=12),
                                         y=1 - 0.08 * (i % 2), yref="paper"),
                         annotation_position="top")
    figura.update_xaxes(tickformat=",.0f")
    return estilo.aplicar(figura, "Valor final (escenarios entre P1 y P99)", f"Valor final ({moneda})",
                          "Número de escenarios", modo, alto=440, leyenda=False)


def comparador_colas(valores_t: np.ndarray, valores_normal: np.ndarray, nu: float, nu_normal: float,
                     limites: tuple[float, float], moneda: str, dia: int, modo: str = "claro") -> go.Figure:
    """Distribución del valor en el día `dia` con el nu elegido frente a un nu alto, misma semilla.

    Eje Y logarítmico para que se vean las colas, que es donde difieren.
    """
    t = estilo.tokens(modo)
    bordes = np.linspace(limites[0], limites[1], 61)
    centros = (bordes[:-1] + bordes[1:]) / 2
    figura = go.Figure()
    trazas = ((valores_normal, f"nu = {nu_normal:g} (casi normal)", t["series"][1], "dash"),
              (valores_t, f"nu = {nu:g} (elegido)", t["series"][0], "solid"))
    for valores, nombre, color, guion in trazas:
        cuenta, _ = np.histogram(valores, bins=bordes)
        porcentaje_escenarios = np.where(cuenta > 0, cuenta / len(valores) * 100, np.nan)
        figura.add_trace(go.Scatter(
            x=centros, y=porcentaje_escenarios, name=nombre, mode="lines", line_shape="hvh",
            line=dict(color=color, width=2.2, dash=guion), connectgaps=False,
            hovertemplate=f"%{{x:,.0f}} {moneda}<br>%{{y:,.3f}} % de escenarios<extra>{nombre}</extra>"))
    figura.update_yaxes(type="log", ticksuffix=" %", exponentformat="none")
    figura.update_xaxes(tickformat=",.0f")
    return estilo.aplicar(figura, f"Efecto de las colas en el día {dia}: misma cartera y semilla, distinto nu",
                          f"Valor de la cartera en el día {dia} ({moneda})",
                          "% de escenarios por intervalo (escala log.)", modo, alto=400)
