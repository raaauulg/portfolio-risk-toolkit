"""Informe en Markdown y gráficos de una cartera (apartado 4.5)."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from .metricas import (
    DIAS_POR_ANIO,
    Rebalanceo,
    caidas,
    concentracion_efectiva,
    contribucion_riesgo,
    cvar_historico,
    ratio_sharpe,
    ratio_sortino,
    rendimientos_simples,
    retorno_anualizado,
    valor_cartera,
    var_historico,
    volatilidad_anualizada,
)
from .simulacion import ResultadoSimulacion
from .visual import (
    COLOR_REJILLA,
    COLOR_ROJO,
    COLOR_SECUNDARIO,
    COLOR_TEXTO,
    COLORES,
    FONDO,
    MAX_SERIES,
    aplicar_estilo,
    finalizar,
)

if TYPE_CHECKING:
    from matplotlib.figure import Figure

SECCIONES = ("resumen", "composicion", "activos", "correlaciones",
             "montecarlo", "diagnostico", "advertencias")
GRAFICOS = ("rendimiento", "correlacion", "evolucion", "riesgo")


@dataclass(frozen=True)
class UmbralesRiesgo:
    """Valores a partir de los cuales el informe genera una advertencia."""

    peso_maximo: float = 0.40
    contribucion_riesgo_maxima: float = 0.50
    correlacion_alta: float = 0.80
    volatilidad_alta: float = 0.25
    caida_alta: float = 0.25
    prob_perdida_alta: float = 0.40
    historia_minima_anios: float = 3.0


def _pct(valor: float, decimales: int = 2) -> str:
    if valor is None or not np.isfinite(valor):
        return "n/d"
    return f"{valor:.{decimales}%}".replace(".", ",").replace("%", " %")


def _num(valor: float, decimales: int = 2) -> str:
    if valor is None or not np.isfinite(valor):
        return "n/d"
    valor = round(float(valor), decimales) + 0.0  # evita mostrar "-0,00"
    return f"{valor:,.{decimales}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def _tabla(cabecera: Sequence[str], filas: Iterable[Sequence[str]]) -> str:
    lineas = ["| " + " | ".join(cabecera) + " |",
              "| " + " | ".join("---" for _ in cabecera) + " |"]
    lineas += ["| " + " | ".join(str(celda) for celda in fila) + " |" for fila in filas]
    return "\n".join(lineas)


def _pares_correlacion(correlacion: pd.DataFrame) -> list[tuple[str, str, float]]:
    """Pares distintos de activos, de mayor a menor correlación."""
    activos = list(correlacion.columns)
    pares = [(activos[i], activos[j], float(correlacion.iloc[i, j]))
             for i in range(len(activos)) for j in range(i + 1, len(activos))]
    return sorted(pares, key=lambda par: par[2], reverse=True)


def _advertencias(
    precios: pd.DataFrame,
    pesos: pd.Series,
    resumen: Mapping[str, float],
    riesgo: pd.Series,
    correlacion: pd.DataFrame,
    umbrales: UmbralesRiesgo,
    simulacion: ResultadoSimulacion | None,
    monedas: Mapping[str, str] | None,
) -> list[tuple[str, str]]:
    avisos: list[tuple[str, str]] = []

    mayor = pesos.abs().idxmax()
    if abs(pesos[mayor]) > umbrales.peso_maximo:
        avisos.append(("ALTO", f"Concentración: {mayor} pesa {_pct(pesos[mayor], 1)}, "
                               f"por encima del límite de {_pct(umbrales.peso_maximo, 0)}."))
    principal = riesgo.idxmax()
    if len(pesos) > 1 and riesgo[principal] > umbrales.contribucion_riesgo_maxima:
        avisos.append(("ALTO", f"Riesgo concentrado: {principal} aporta "
                               f"{_pct(riesgo[principal], 1)} del riesgo con un peso de "
                               f"{_pct(pesos[principal], 1)}."))
    if resumen["volatilidad"] > umbrales.volatilidad_alta:
        avisos.append(("MEDIO", f"Volatilidad elevada: {_pct(resumen['volatilidad'], 1)} anual."))
    if resumen["caida_maxima"] < -umbrales.caida_alta:
        avisos.append(("ALTO", f"Caída máxima histórica de {_pct(resumen['caida_maxima'], 1)}."))
    for activo_a, activo_b, valor in _pares_correlacion(correlacion):
        if valor < umbrales.correlacion_alta:
            break
        avisos.append(("MEDIO", f"Poca diversificación entre {activo_a} y {activo_b}: "
                                f"correlación de {_num(valor)}."))
    if (pesos < 0).any():
        avisos.append(("ALTO", "La cartera tiene posiciones cortas: la pérdida potencial "
                               "puede superar el capital invertido."))
    if resumen["anios"] < umbrales.historia_minima_anios:
        avisos.append(("MEDIO", f"Historia corta: {_num(resumen['anios'], 1)} años de datos "
                                "comunes; las estimaciones son poco fiables."))
    if monedas and len(set(monedas.values())) > 1:
        avisos.append(("ALTO", "Activos en varias monedas "
                               f"({', '.join(sorted(set(monedas.values())))}): los precios no "
                               "están convertidos a una moneda común."))
    if simulacion is not None:
        if simulacion.prob_perdida() > umbrales.prob_perdida_alta:
            avisos.append(("MEDIO", "Monte Carlo: probabilidad de pérdida de "
                                    f"{_pct(simulacion.prob_perdida(), 1)} en el horizonte."))
        if simulacion.parametros.retorno_anual is None:
            avisos.append(("INFO", "Monte Carlo usa el retorno histórico como retorno futuro. "
                                   "Es el supuesto más débil: conviene probar otros valores."))
    avisos.append(("INFO", "Las métricas son históricas o simuladas, no garantizan resultados "
                           "futuros, y no incluyen costes, impuestos ni dividendos salvo que "
                           "los precios ya estén ajustados."))
    orden = {"ALTO": 0, "MEDIO": 1, "INFO": 2}
    return sorted(avisos, key=lambda aviso: orden[aviso[0]])


def generar_report(
    precios: pd.DataFrame,
    pesos: pd.Series,
    nombre: str = "Cartera",
    tasa_libre: float = 0.0,
    nivel_var: float = 0.95,
    rebalanceo: Rebalanceo = "diario",
    benchmark: pd.Series | None = None,
    simulacion: ResultadoSimulacion | None = None,
    secciones: Sequence[str] = SECCIONES,
    umbrales: UmbralesRiesgo | None = None,
    incidencias: Sequence[str] = (),
    monedas: Mapping[str, str] | None = None,
    dias_por_anio: int = DIAS_POR_ANIO,
    ruta: str | Path | None = None,
) -> str:
    """Genera el informe en Markdown. precios deben estar limpios y alineados.

    secciones elige qué partes incluir, de entre SECCIONES. Si se indica ruta,
    también se guarda en un archivo .md.
    """
    desconocidas = sorted(set(secciones) - set(SECCIONES))
    if desconocidas:
        raise ValueError(f"Secciones desconocidas: {desconocidas}. Opciones: {SECCIONES}.")
    if not 0.5 < nivel_var < 1.0:
        raise ValueError("nivel_var debe estar entre 0,5 y 1.")
    umbrales = umbrales or UmbralesRiesgo()

    rendimientos = rendimientos_simples(precios)
    valores = valor_cartera(precios, pesos, rebalanceo)
    rend_cartera = rendimientos_simples(valores)
    correlacion = rendimientos.corr()
    riesgo = contribucion_riesgo(rendimientos, pesos)

    resumen = {
        "retorno": retorno_anualizado(valores, dias_por_anio),
        "volatilidad": volatilidad_anualizada(rend_cartera, dias_por_anio),
        "sharpe": ratio_sharpe(rend_cartera, tasa_libre, dias_por_anio),
        "sortino": ratio_sortino(rend_cartera, tasa_libre, dias_por_anio),
        "caida_maxima": float(caidas(valores).min()),
        "var": var_historico(rend_cartera, nivel_var),
        "cvar": cvar_historico(rend_cartera, nivel_var),
        "anios": len(rend_cartera) / dias_por_anio,
    }
    nivel = _pct(nivel_var, 0)
    bloques: list[str] = [f"# Informe de {nombre}"]

    if "resumen" in secciones:
        filas = [
            ("Periodo", f"{precios.index[0]:%d/%m/%Y} a {precios.index[-1]:%d/%m/%Y} "
                        f"({len(precios)} sesiones)"),
            ("Rendimiento anualizado", _pct(resumen["retorno"])),
            ("Volatilidad anualizada", _pct(resumen["volatilidad"])),
            (f"Ratio de Sharpe (tasa libre {_pct(tasa_libre)})", _num(resumen["sharpe"])),
            ("Ratio de Sortino", _num(resumen["sortino"])),
            ("Caída máxima", _pct(resumen["caida_maxima"])),
            (f"VaR diario histórico al {nivel}", _pct(resumen["var"])),
            (f"CVaR diario histórico al {nivel}", _pct(resumen["cvar"])),
            ("Rebalanceo", rebalanceo),
        ]
        if benchmark is not None:
            comunes = rend_cartera.index.intersection(benchmark.index)
            rend_ref = rendimientos_simples(benchmark.reindex(precios.index).ffill()).reindex(comunes)
            valido = rend_ref.notna()
            cartera_ref, rend_ref = rend_cartera.reindex(comunes)[valido], rend_ref[valido]
            if len(rend_ref) > 2 and rend_ref.var() > 0:
                beta = float(rend_ref.cov(cartera_ref) / rend_ref.var())
                error = volatilidad_anualizada(cartera_ref - rend_ref, dias_por_anio)
                ref = str(benchmark.name or "referencia")
                filas += [(f"Beta frente a {ref}", _num(beta)),
                          (f"Tracking error frente a {ref}", _pct(error))]
        bloques.append("## Resumen\n\n" + _tabla(("Métrica", "Valor"), filas))

    if "composicion" in secciones:
        filas = [(activo, _pct(pesos[activo], 1), _pct(riesgo[activo], 1))
                 for activo in pesos.sort_values(ascending=False).index]
        bloques.append(
            "## Composición\n\n"
            + _tabla(("Activo", "Peso", "Aportación al riesgo"), filas)
            + f"\n\nNúmero efectivo de activos: {_num(concentracion_efectiva(pesos), 1)} "
              f"de {len(pesos)}."
        )

    if "activos" in secciones:
        filas = []
        for activo in precios.columns:
            serie = precios[activo]
            rend = rendimientos[activo]
            filas.append((activo,
                          _pct(retorno_anualizado(serie, dias_por_anio)),
                          _pct(volatilidad_anualizada(rend, dias_por_anio)),
                          _num(ratio_sharpe(rend, tasa_libre, dias_por_anio)),
                          _pct(float(caidas(serie).min()))))
        bloques.append("## Métricas por activo\n\n"
                       + _tabla(("Activo", "Rendimiento anual", "Volatilidad", "Sharpe",
                                 "Caída máxima"), filas))

    if "correlaciones" in secciones and len(pesos) > 1:
        pares = _pares_correlacion(correlacion)
        texto = (f"Media entre pares: {_num(float(np.mean([p[2] for p in pares])))}. "
                 f"Más alta: {pares[0][0]}/{pares[0][1]} ({_num(pares[0][2])}). "
                 f"Más baja: {pares[-1][0]}/{pares[-1][1]} ({_num(pares[-1][2])}).")
        bloques.append("## Correlaciones\n\n" + texto)

    if "montecarlo" in secciones and simulacion is not None:
        datos = simulacion.resumen(nivel_var)
        parametros = simulacion.parametros
        filas = [
            ("Escenarios", f"{parametros.n_iteraciones:,}".replace(",", ".")),
            ("Horizonte", f"{parametros.horizonte_dias} días de mercado"),
            ("Valor inicial", _num(datos["valor_inicial"])),
            ("Valor final mediano", _num(datos["valor_mediano"])),
            ("Rango central del 90 %", f"{_num(datos['percentil_5'])} a {_num(datos['percentil_95'])}"),
            ("Probabilidad de pérdida", _pct(datos["prob_perdida"], 1)),
            (f"VaR al {nivel} en el horizonte", _pct(datos["var"])),
            (f"CVaR al {nivel} en el horizonte", _pct(datos["cvar"])),
        ]
        bloques.append("## Simulación de Monte Carlo\n\n" + _tabla(("Métrica", "Valor"), filas))

    if "diagnostico" in secciones:
        if incidencias:
            lista = "\n".join(f"- {texto}" for texto in incidencias)
        else:
            lista = "- No se han detectado incidencias."
        bloques.append("## Diagnóstico de los datos\n\n" + lista)

    if "advertencias" in secciones:
        avisos = _advertencias(precios, pesos, resumen, riesgo, correlacion, umbrales,
                               simulacion, monedas)
        bloques.append("## Advertencias de riesgo\n\n"
                       + "\n".join(f"- **{nivel_aviso}:** {texto}" for nivel_aviso, texto in avisos))

    informe = "\n\n".join(bloques) + "\n"
    if ruta is not None:
        destino = Path(ruta)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(informe, encoding="utf-8")
    return informe


def _grafico_rendimiento(precios, pesos, valores, benchmark, nombre):
    import matplotlib.pyplot as plt

    figura, eje = plt.subplots(figsize=(10, 5.2), facecolor=FONDO, layout="constrained")
    principales = pesos.abs().sort_values(ascending=False).index[:MAX_SERIES]
    series: list[tuple[str, pd.Series, str]] = []
    for posicion, activo in enumerate(precios.columns.intersection(principales, sort=False)):
        base_100 = precios[activo] / precios[activo].iloc[0] * 100
        series.append((activo, base_100, COLORES[posicion]))
        eje.plot(base_100.index, base_100, color=COLORES[posicion], linewidth=1.2, label=activo)
    if benchmark is not None:
        referencia = benchmark.reindex(precios.index).ffill().dropna()
        base_ref = referencia / referencia.iloc[0] * 100
        etiqueta = str(benchmark.name or "Referencia")
        series.append((etiqueta, base_ref, COLOR_SECUNDARIO))
        eje.plot(base_ref.index, base_ref, color=COLOR_SECUNDARIO, linewidth=1.4,
                 linestyle="--", label=etiqueta)
    series.append((nombre, valores, COLOR_TEXTO))
    eje.plot(valores.index, valores, color=COLOR_TEXTO, linewidth=2.4, label=nombre)
    eje.axhline(100, color=COLOR_REJILLA, linewidth=1)

    if len(series) <= 4:  # etiquetas directas, separadas para que no se pisen
        finales = sorted((serie.iloc[-1], etiqueta) for etiqueta, serie, _ in series)
        separacion = (eje.get_ylim()[1] - eje.get_ylim()[0]) * 0.045
        ultima_y = -np.inf
        for valor, etiqueta in finales:
            ultima_y = max(valor, ultima_y + separacion)
            eje.annotate(etiqueta, (precios.index[-1], ultima_y), xytext=(6, 0),
                         textcoords="offset points", va="center", fontsize=9,
                         color=COLOR_TEXTO, annotation_clip=False)
    eje.margins(x=0)
    eje.set_ylabel("Base 100")
    eje.set_title(f"Rendimiento acumulado de {nombre} y sus activos", loc="left",
                  color=COLOR_TEXTO, fontsize=13, fontweight="bold")
    eje.legend(frameon=False, ncols=min(len(series), 5), loc="upper left", fontsize=9)
    aplicar_estilo(eje)
    return figura


def _grafico_correlacion(rendimientos, nombre):
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    correlacion = rendimientos.corr()
    n = len(correlacion)
    lado = max(5.0, min(0.75 * n + 2.5, 11.0))
    figura, eje = plt.subplots(figsize=(lado + 0.8, lado), facecolor=FONDO, layout="constrained")
    mapa = LinearSegmentedColormap.from_list("azul_rojo", ["#256abf", "#f0efec", COLOR_ROJO])
    imagen = eje.imshow(correlacion, cmap=mapa, vmin=-1, vmax=1)
    eje.set_xticks(range(n), correlacion.columns, rotation=45, ha="right")
    eje.set_yticks(range(n), correlacion.index)
    if n <= 12:
        for fila in range(n):
            for columna in range(n):
                valor = correlacion.iloc[fila, columna]
                color = "white" if abs(valor) > 0.65 else COLOR_TEXTO
                eje.text(columna, fila, _num(valor), ha="center", va="center",
                         fontsize=9, color=color)
    eje.tick_params(colors=COLOR_SECUNDARIO, labelsize=9, length=0)
    for lado_eje in eje.spines.values():
        lado_eje.set_visible(False)
    eje.set_title(f"Correlación de rendimientos diarios: {nombre}", loc="left",
                  color=COLOR_TEXTO, fontsize=13, fontweight="bold")
    barra = figura.colorbar(imagen, ax=eje, shrink=0.8)
    barra.outline.set_visible(False)
    barra.ax.tick_params(colors=COLOR_SECUNDARIO, labelsize=8, length=0)
    return figura


def _grafico_evolucion(valores, nombre):
    import matplotlib.pyplot as plt

    figura, (eje_valor, eje_caida) = plt.subplots(
        2, 1, figsize=(10, 6), sharex=True, height_ratios=[2, 1],
        facecolor=FONDO, layout="constrained",
    )
    eje_valor.plot(valores.index, valores, color=COLORES[0], linewidth=2)
    eje_valor.set_ylabel("Valor (inicio = 100)")
    eje_valor.set_title(f"Evolución y caídas de {nombre}", loc="left",
                        color=COLOR_TEXTO, fontsize=13, fontweight="bold")
    caida = caidas(valores) * 100
    eje_caida.fill_between(caida.index, caida, 0, color=COLOR_ROJO, alpha=0.35, linewidth=0)
    eje_caida.plot(caida.index, caida, color=COLOR_ROJO, linewidth=1)
    fecha_minimo = caida.idxmin()
    a_la_derecha = fecha_minimo < valores.index[len(valores) // 2]
    eje_caida.annotate(f"Máxima: {_num(caida.min(), 1)} %", (fecha_minimo, caida.min()),
                       xytext=(8 if a_la_derecha else -8, 0), textcoords="offset points",
                       ha="left" if a_la_derecha else "right", va="center",
                       fontsize=9, color=COLOR_TEXTO)
    eje_caida.set_ylabel("Caída desde máximos (%)")
    eje_caida.margins(x=0)
    eje_caida.set_ylim(top=0)
    for eje in (eje_valor, eje_caida):
        aplicar_estilo(eje)
    return figura


def _grafico_riesgo(rendimientos, pesos, rend_cartera, ventana_volatilidad, dias_por_anio, nombre):
    import matplotlib.pyplot as plt
    from matplotlib.dates import AutoDateLocator, DateFormatter

    figura, (eje_vol, eje_barras) = plt.subplots(
        1, 2, figsize=(11, 5), width_ratios=[3, 2], facecolor=FONDO, layout="constrained",
    )
    movil = rend_cartera.rolling(ventana_volatilidad).std() * np.sqrt(dias_por_anio) * 100
    eje_vol.plot(movil.index, movil, color=COLORES[0], linewidth=1.8)
    eje_vol.axhline(movil.mean(), color=COLOR_SECUNDARIO, linewidth=1, linestyle="--",
                    label=f"Media: {_num(movil.mean(), 1)} %")
    eje_vol.set_ylabel("Volatilidad anualizada (%)")
    eje_vol.set_title(f"Volatilidad móvil ({ventana_volatilidad} sesiones)", loc="left",
                      color=COLOR_TEXTO, fontsize=11)
    eje_vol.margins(x=0)
    eje_vol.set_ylim(bottom=0)
    eje_vol.xaxis.set_major_locator(AutoDateLocator(minticks=3, maxticks=8))
    eje_vol.xaxis.set_major_formatter(DateFormatter("%m/%Y"))
    eje_vol.legend(frameon=False, fontsize=9)

    riesgo = contribucion_riesgo(rendimientos, pesos) * 100
    orden = riesgo.sort_values().index[-MAX_SERIES:]
    posiciones = np.arange(len(orden))
    alto = 0.36
    eje_barras.barh(posiciones + alto / 2 + 0.02, pesos[orden] * 100, height=alto,
                    color=COLORES[0], label="Peso")
    eje_barras.barh(posiciones - alto / 2 - 0.02, riesgo[orden], height=alto,
                    color=COLORES[1], label="Aportación al riesgo")
    eje_barras.set_yticks(posiciones, orden)
    eje_barras.set_xlabel("%")
    eje_barras.set_title("Peso frente a riesgo aportado", loc="left", color=COLOR_TEXTO, fontsize=11)
    eje_barras.legend(frameon=False, fontsize=9, loc="lower right")
    for eje in (eje_vol, eje_barras):
        aplicar_estilo(eje)
    eje_barras.grid(False, axis="y")
    figura.suptitle(f"Riesgo de {nombre}", x=0.01, ha="left", color=COLOR_TEXTO,
                    fontsize=13, fontweight="bold")
    return figura


def generar_plots(
    precios: pd.DataFrame,
    pesos: pd.Series,
    nombre: str = "Cartera",
    rebalanceo: Rebalanceo = "diario",
    benchmark: pd.Series | None = None,
    graficos: Sequence[str] = GRAFICOS,
    ventana_volatilidad: int = 63,
    dias_por_anio: int = DIAS_POR_ANIO,
    mostrar: bool = True,
    carpeta: str | Path | None = None,
) -> dict[str, "Figure"]:
    """Crea los gráficos pedidos y los devuelve en un diccionario {nombre: figura}.

    Si se indica carpeta, guarda cada gráfico como PNG en ella.
    """
    desconocidos = sorted(set(graficos) - set(GRAFICOS))
    if desconocidos:
        raise ValueError(f"Gráficos desconocidos: {desconocidos}. Opciones: {GRAFICOS}.")
    rendimientos = rendimientos_simples(precios)
    valores = valor_cartera(precios, pesos, rebalanceo)
    rend_cartera = rendimientos_simples(valores)

    constructores = {
        "rendimiento": lambda: _grafico_rendimiento(precios, pesos, valores, benchmark, nombre),
        "correlacion": lambda: _grafico_correlacion(rendimientos, nombre),
        "evolucion": lambda: _grafico_evolucion(valores, nombre),
        "riesgo": lambda: _grafico_riesgo(rendimientos, pesos, rend_cartera,
                                          ventana_volatilidad, dias_por_anio, nombre),
    }
    figuras = {}
    for clave in graficos:
        ruta = Path(carpeta) / f"{clave}.png" if carpeta is not None else None
        figuras[clave] = finalizar(constructores[clave](), mostrar=False, ruta=ruta)
    if mostrar:
        import matplotlib.pyplot as plt

        plt.show()
    return figuras
