"""Informe en Markdown y gráficos de una cartera (apartado 4.5).

Este módulo no importa Cartera: recibe precios ya limpios y alineados, pesos
y, opcionalmente, el resultado del Monte Carlo. Reutiliza las validaciones de
limpieza y limpia la referencia cuando se proporciona un benchmark.

La cartera se valora como "comprar y mantener" (igual que el Monte Carlo):
se invierte según los pesos el primer día y no se rebalancea.
"""

import numpy as np
import pandas as pd
from numbers import Real

from .limpieza import limpiar_precios, validar_pesos, validar_tabla

DIAS_POR_ANIO = 252

SECCIONES = ("resumen", "composicion", "activos", "correlaciones",
             "montecarlo", "diagnostico", "advertencias")
GRAFICOS = ("rendimiento", "correlacion", "evolucion", "riesgo")

# Límites a partir de los cuales el informe avisa (se pueden cambiar al llamar)
UMBRALES = {
    "peso_maximo": 0.40,          # un activo pesa más del 40 %
    "riesgo_maximo": 0.50,        # un activo aporta más del 50 % del riesgo
    "volatilidad_alta": 0.25,     # volatilidad anual de la cartera > 25 %
    "caida_alta": 0.25,           # caída máxima histórica > 25 %
    "correlacion_alta": 0.80,     # dos activos con correlación > 0,8
    "historia_minima_anios": 1.0, # menos de un año de datos comunes
    "prob_perdida_alta": 0.40,    # Monte Carlo: más de un 40 % de escenarios con pérdida
}

COLORES = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100",
           "#e87ba4", "#008300", "#6250d6", "#e34948")


# ---------- Métricas ----------

def valor_cartera(precios: pd.DataFrame, pesos: pd.Series, v0: float = 100.0) -> pd.Series:
    """Valor de la cartera comprando el primer día y manteniendo: v0 * suma(peso * P(t) / P(0))."""
    pesos = pd.Series(pesos, dtype=float).reindex(precios.columns)
    valores = v0 * (precios / precios.iloc[0]) @ pesos
    return valores.rename("Cartera")


def metricas(valores: pd.Series, tasa_libre: float = 0.0, nivel_var: float = 0.95) -> dict:
    """Métricas principales de una serie de valores (precio o valor de cartera)."""
    if not isinstance(valores, pd.Series) or valores.empty or not np.isfinite(valores).all() or (valores <= 0).any():
        raise ValueError("Se necesitan valores positivos y finitos para calcular métricas.")
    if (any(isinstance(x, (bool, np.bool_)) or not isinstance(x, Real)
            or not np.isfinite(x) for x in (tasa_libre, nivel_var))
            or not 0.5 < nivel_var < 1):
        raise ValueError("La tasa libre debe ser finita y nivel_var debe estar entre 0,5 y 1.")
    rend = valores.pct_change(fill_method=None).dropna()
    n = len(rend)
    anios = n / DIAS_POR_ANIO
    resultado = {"anios": anios, "rent_total": valores.iloc[-1] / valores.iloc[0] - 1}
    if n < 2:  # con menos de dos rendimientos no se puede calcular la dispersión
        resultado.update(rent_anual=np.nan, volatilidad=np.nan, sharpe=np.nan,
                         sortino=np.nan, var=np.nan, cvar=np.nan,
                         caida_maxima=float((valores / valores.cummax() - 1).min()))
        return resultado

    volatilidad = rend.std() * np.sqrt(DIAS_POR_ANIO)
    rent_anual = (1 + resultado["rent_total"]) ** (1 / anios) - 1
    exceso = rend - tasa_libre / DIAS_POR_ANIO
    riesgo_bajista = np.sqrt((exceso.clip(upper=0) ** 2).mean()) * np.sqrt(DIAS_POR_ANIO)
    corte = rend.quantile(1 - nivel_var)

    resultado.update(
        rent_anual=rent_anual,
        volatilidad=volatilidad,
        sharpe=(rend.mean() * DIAS_POR_ANIO - tasa_libre) / volatilidad if volatilidad > 0 else np.nan,
        sortino=exceso.mean() * DIAS_POR_ANIO / riesgo_bajista if riesgo_bajista > 0 else np.nan,
        caida_maxima=float((valores / valores.cummax() - 1).min()),
        var=-corte,                              # pérdida diaria que solo se supera el (1 - nivel) de los días
        cvar=-rend[rend <= corte].mean(),        # pérdida media de esos peores días
    )
    return resultado


def contribucion_riesgo(precios: pd.DataFrame, pesos: pd.Series) -> pd.Series:
    """Aproximación con pesos iniciales fijos; no sigue su deriva en comprar y mantener."""
    pesos = pd.Series(pesos, dtype=float).reindex(precios.columns)
    cov = precios.pct_change().dropna().cov()
    aportes = pesos * (cov @ pesos)
    return aportes / aportes.sum() if aportes.sum() > 0 else aportes * np.nan


# ---------- Formato ----------

def _pct(x, decimales=2):
    if x is None or not np.isfinite(x):
        return "n/d"
    return f"{x * 100:.{decimales}f} %".replace(".", ",")


def _num(x, decimales=2):
    if x is None or not np.isfinite(x):
        return "n/d"
    return f"{x:.{decimales}f}".replace(".", ",")


def _tabla(cabecera, filas):
    lineas = ["| " + " | ".join(cabecera) + " |", "|" + " --- |" * len(cabecera)]
    lineas += ["| " + " | ".join(str(c) for c in fila) + " |" for fila in filas]
    return "\n".join(lineas)


def _pares_correlacion(correlacion: pd.DataFrame):
    """Pares de activos distintos, de mayor a menor correlación."""
    activos = list(correlacion.columns)
    pares = [(activos[i], activos[j], correlacion.iloc[i, j])
             for i in range(len(activos)) for j in range(i + 1, len(activos))
             if np.isfinite(correlacion.iloc[i, j])]
    return sorted(pares, key=lambda p: p[2], reverse=True)


# ---------- Informe ----------

def _advertencias(m, pesos, riesgo, correlacion, umbrales, diagnostico, monedas, simulacion):
    """Lista de (nivel, texto) ordenada de más a menos grave."""
    avisos = []
    mayor = pesos.idxmax()
    if pesos[mayor] > umbrales["peso_maximo"]:
        avisos.append(("ALTO", f"Concentración: {mayor} pesa un {_pct(pesos[mayor], 1)} "
                               f"(límite {_pct(umbrales['peso_maximo'], 0)})."))
    principal = riesgo.idxmax() if riesgo.notna().any() else None
    if principal is None:
        avisos.append(("INFO", "Aportación al riesgo no disponible: la varianza es nula o no estimable."))
    if principal is not None and len(pesos) > 1 and riesgo[principal] > umbrales["riesgo_maximo"]:
        avisos.append(("ALTO", f"Riesgo concentrado: {principal} aporta el {_pct(riesgo[principal], 1)} "
                               f"del riesgo con un peso del {_pct(pesos[principal], 1)}."))
    if np.isfinite(m["volatilidad"]) and m["volatilidad"] > umbrales["volatilidad_alta"]:
        avisos.append(("MEDIO", f"Volatilidad elevada: {_pct(m['volatilidad'], 1)} anual."))
    if m["caida_maxima"] < -umbrales["caida_alta"]:
        avisos.append(("ALTO", f"Caída máxima histórica del {_pct(-m['caida_maxima'], 1)}."))
    for a, b, rho in _pares_correlacion(correlacion):
        if rho > umbrales["correlacion_alta"]:
            avisos.append(("MEDIO", f"Poca diversificación entre {a} y {b}: correlación de {_num(rho)}."))
    if m["anios"] < umbrales["historia_minima_anios"]:
        avisos.append(("MEDIO", f"Historia corta ({_num(m['anios'], 2)} años de datos comunes): "
                                "las métricas anualizadas son poco fiables."))
    if monedas and len(set(monedas.values())) > 1:
        avisos.append(("ALTO", f"La cartera mezcla monedas ({', '.join(sorted(set(monedas.values())))}) "
                               "y los precios no están convertidos."))
    for linea in diagnostico:
        if linea.startswith("AVISO"):
            avisos.append(("MEDIO", "Datos: " + linea.removeprefix("AVISO ")))
    if simulacion is not None:
        prob = simulacion.resumen()["prob_perdida"]
        if prob > umbrales["prob_perdida_alta"]:
            avisos.append(("MEDIO", f"Monte Carlo: {_pct(prob, 1)} de escenarios terminan con pérdidas."))
    avisos.append(("INFO", "Métricas históricas y escenarios simulados: no garantizan resultados futuros "
                           "y no incluyen costes ni impuestos."))
    orden = {"ALTO": 0, "MEDIO": 1, "INFO": 2}
    return sorted(avisos, key=lambda a: orden[a[0]])


def _alinear_benchmark(precios, benchmark):
    """Compara sobre fechas reales comunes; nunca rellena cotizaciones ausentes."""
    if benchmark is None:
        return precios, None, []
    referencia, diagnostico = limpiar_precios(benchmark, nombre="benchmark")
    comunes = precios.index.intersection(referencia.index)
    if len(comunes) < 3:
        raise ValueError("El benchmark necesita al menos 3 fechas válidas comunes con la cartera.")
    tabla = precios.loc[comunes]
    validar_tabla(tabla)
    return tabla, referencia.loc[comunes], diagnostico


def generar_report(
    precios: pd.DataFrame,
    pesos,
    nombre: str = "Cartera",
    secciones=SECCIONES,
    tasa_libre: float = 0.0,
    nivel_var: float = 0.95,
    benchmark: pd.Series | None = None,
    simulacion=None,
    diagnostico=(),
    monedas: dict | None = None,
    umbrales: dict | None = None,
    ruta=None,
) -> str:
    """Genera el informe en Markdown de una cartera.

    precios: tabla limpia y alineada (una columna por activo).
    secciones: cuáles incluir, de entre SECCIONES.
    tasa_libre: tipo libre de riesgo anual para Sharpe y Sortino.
    nivel_var: nivel de confianza del VaR y CVaR (0,95 = 95 %).
    benchmark: serie de un índice de referencia, para calcular beta.
    simulacion: resultado de monte_carlo(), si se quiere incluir.
    diagnostico: líneas del resumen de la limpieza.
    umbrales: cambia los límites de las advertencias, p. ej. {"peso_maximo": 0.3}.
    ruta: si se indica, guarda el informe en ese archivo .md.
    """
    desconocidas = set(secciones) - set(SECCIONES)
    if desconocidas:
        raise ValueError(f"Secciones desconocidas: {sorted(desconocidas)}. Opciones: {SECCIONES}.")
    if (isinstance(nivel_var, (bool, np.bool_)) or not isinstance(nivel_var, Real)
            or not 0.5 < nivel_var < 1):
        raise ValueError("nivel_var debe estar entre 0,5 y 1.")
    if umbrales and set(umbrales) - set(UMBRALES):
        raise ValueError("Hay nombres de umbrales desconocidos.")
    umbrales = {**UMBRALES, **(umbrales or {})}
    if any(isinstance(v, (bool, np.bool_)) or not isinstance(v, Real)
           or not np.isfinite(v) or v < 0 for v in umbrales.values()):
        raise ValueError("Los umbrales deben ser finitos y no negativos.")
    validar_tabla(precios)
    antes = len(precios)
    precios, benchmark, diagnostico_ref = _alinear_benchmark(precios, benchmark)
    diagnostico = list(diagnostico) + diagnostico_ref
    if benchmark is not None:
        diagnostico.append(f"Benchmark: análisis sobre {len(precios)} de {antes} fechas comunes, sin rellenar precios.")

    pesos = validar_pesos(pesos, precios.columns)
    valores = valor_cartera(precios, pesos)
    m = metricas(valores, tasa_libre, nivel_var)
    correlacion = precios.pct_change().dropna().corr()
    riesgo = contribucion_riesgo(precios, pesos)
    nivel = _pct(nivel_var, 0)

    bloques = [f"# Informe de {nombre}",
               f"Periodo: {precios.index[0]:%d/%m/%Y} a {precios.index[-1]:%d/%m/%Y} "
               f"({len(precios)} sesiones). Cartera de comprar y mantener."]

    if "resumen" in secciones:
        filas = [
            ("Rentabilidad total", _pct(m["rent_total"])),
            ("Rentabilidad anualizada", _pct(m["rent_anual"])),
            ("Volatilidad anualizada", _pct(m["volatilidad"])),
            (f"Ratio de Sharpe (tasa libre {_pct(tasa_libre)})", _num(m["sharpe"])),
            ("Ratio de Sortino", _num(m["sortino"])),
            ("Caída máxima", _pct(m["caida_maxima"])),
            (f"VaR diario histórico al {nivel}", _pct(m["var"])),
            (f"CVaR diario histórico al {nivel}", _pct(m["cvar"])),
        ]
        if benchmark is not None:
            ref = benchmark
            r_cartera, r_ref = valores.pct_change(), ref.pct_change()
            validos = r_cartera.notna() & r_ref.notna()
            if validos.sum() > 2 and r_ref[validos].var() > 0:
                beta = r_cartera[validos].cov(r_ref[validos]) / r_ref[validos].var()
                filas.append((f"Beta frente a {benchmark.name or 'referencia'}", _num(beta)))
        bloques.append("## Métricas de la cartera\n\n" + _tabla(("Métrica", "Valor"), filas))

    if "composicion" in secciones:
        filas = [(a, _pct(pesos[a], 1), _pct(riesgo[a], 1))
                 for a in pesos.sort_values(ascending=False).index]
        efectivos = 1 / (pesos ** 2).sum()
        bloques.append("## Composición\n\n" + _tabla(("Activo", "Peso", "Aportación al riesgo"), filas)
                       + "\n\nAportación al riesgo aproximada con pesos iniciales fijos; los pesos efectivos de comprar y mantener cambian."
                       + f"\n\nNúmero efectivo de activos: {_num(efectivos, 1)} de {len(pesos)} "
                         "(si todos pesaran igual, coincidiría con el total).")

    if "activos" in secciones:
        filas = []
        for a in precios.columns:
            ma = metricas(precios[a], tasa_libre, nivel_var)
            filas.append((a, _pct(ma["rent_anual"]), _pct(ma["volatilidad"]),
                          _num(ma["sharpe"]), _pct(ma["caida_maxima"])))
        bloques.append("## Métricas por activo\n\n"
                       + _tabla(("Activo", "Rentabilidad anual", "Volatilidad", "Sharpe", "Caída máxima"), filas))

    if "correlaciones" in secciones and len(pesos) > 1:
        pares = _pares_correlacion(correlacion)
        if not pares:
            bloques.append("## Correlaciones\n\nNo disponibles: no hay pares con variación suficiente.")
        else:
            media = np.mean([p[2] for p in pares])
            bloques.append(
                "## Correlaciones\n\n"
                f"Correlación media entre pares: {_num(media)}. "
                f"Más alta: {pares[0][0]} / {pares[0][1]} ({_num(pares[0][2])}). "
                f"Más baja: {pares[-1][0]} / {pares[-1][1]} ({_num(pares[-1][2])})."
            )

    if "montecarlo" in secciones and simulacion is not None:
        r = simulacion.resumen()
        p = simulacion.parametros
        filas = [
            ("Escenarios", f"{len(simulacion.trayectorias):,}".replace(",", ".")),
            ("Horizonte", f"{simulacion.trayectorias.shape[1] - 1} días de mercado"),
            ("Grados de libertad (nu)", str(p.get("nu", "n/d"))),
            ("Valor inicial", _num(r["valor_inicial"])),
            ("P5 / P50 / P95", f"{_num(r['P5'])} / {_num(r['P50'])} / {_num(r['P95'])}"),
            ("Probabilidad de pérdida", _pct(r["prob_perdida"], 1)),
        ]
        if "fecha_inicio" in p and "fecha_fin" in p:
            filas.append(("Histórico de calibración", f"{p['fecha_inicio']} a {p['fecha_fin']}"))
        bloques.append("## Simulación de Monte Carlo\n\n" + _tabla(("Métrica", "Valor"), filas)
                       + "\n\nSon escenarios posibles según los supuestos del modelo, no predicciones.")

    if "diagnostico" in secciones:
        lineas = [f"- {l}" for l in diagnostico] or ["- No se ha recibido diagnóstico de limpieza."]
        bloques.append("## Diagnóstico de los datos\n\n" + "\n".join(lineas))

    if "advertencias" in secciones:
        avisos = _advertencias(m, pesos, riesgo, correlacion, umbrales, list(diagnostico), monedas, simulacion)
        bloques.append("## Advertencias de riesgo\n\n"
                       + "\n".join(f"- **{nivel_aviso}:** {texto}" for nivel_aviso, texto in avisos))

    informe = "\n\n".join(bloques) + "\n"
    if ruta is not None:
        with open(ruta, "w", encoding="utf-8") as archivo:
            archivo.write(informe)
    return informe


# ---------- Gráficos ----------

def _estilo(eje):
    eje.spines[["top", "right"]].set_visible(False)
    eje.grid(alpha=0.3)


def _grafico_rendimiento(precios, valores, benchmark, nombre):
    import matplotlib.pyplot as plt

    figura, eje = plt.subplots(figsize=(10, 5), layout="constrained")
    for i, a in enumerate(precios.columns):
        eje.plot(precios.index, 100 * precios[a] / precios[a].iloc[0], color=COLORES[i % len(COLORES)],
                 linewidth=1.2, label=a)
    if benchmark is not None:
        ref = benchmark
        eje.plot(ref.index, 100 * ref / ref.iloc[0], color="#52514e", linestyle="--",
                 linewidth=1.4, label=str(benchmark.name or "Referencia"))
    eje.plot(valores.index, valores, color="black", linewidth=2.5, label=nombre)
    eje.axhline(100, color="#999999", linewidth=0.8)
    eje.set_ylabel("Base 100")
    eje.set_title(f"Rendimiento acumulado: {nombre} frente a sus activos", loc="left",
                  fontweight="bold", pad=28)
    eje.legend(frameon=False, ncols=min(6, len(precios.columns) + 2), loc="lower left",
               bbox_to_anchor=(0, 1.01), borderaxespad=0)
    eje.margins(x=0)
    _estilo(eje)
    return figura


def _grafico_correlacion(precios, nombre):
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    corr = precios.pct_change().dropna().corr()
    n = len(corr)
    lado = min(max(4.5, 0.7 * n + 2.5), 10)
    figura, eje = plt.subplots(figsize=(lado + 1, lado), layout="constrained")
    mapa = LinearSegmentedColormap.from_list("div", ["#256abf", "#f0efec", "#e34948"])
    imagen = eje.imshow(corr, cmap=mapa, vmin=-1, vmax=1)
    eje.set_xticks(range(n), corr.columns, rotation=45, ha="right")
    eje.set_yticks(range(n), corr.index)
    if n <= 12:
        for i in range(n):
            for j in range(n):
                valor = corr.iloc[i, j]
                eje.text(j, i, _num(valor), ha="center", va="center", fontsize=9,
                         color="white" if abs(valor) > 0.65 else "black")
    eje.set_title(f"Correlación de rendimientos diarios\n{nombre}", loc="left", fontweight="bold")
    figura.colorbar(imagen, ax=eje, shrink=0.8)
    return figura


def _grafico_evolucion(valores, nombre):
    import matplotlib.pyplot as plt

    figura, (eje1, eje2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True,
                                         height_ratios=[2, 1], layout="constrained")
    eje1.plot(valores.index, valores, color=COLORES[0], linewidth=2)
    eje1.set_ylabel("Valor (inicio = 100)")
    eje1.set_title(f"Evolución y caídas de {nombre}", loc="left", fontweight="bold")

    caida = (valores / valores.cummax() - 1) * 100
    eje2.fill_between(caida.index, caida, 0, color="#e34948", alpha=0.35, linewidth=0)
    eje2.plot(caida.index, caida, color="#e34948", linewidth=1)
    eje2.set_ylabel("Caída desde máximos (%)")
    eje2.set_ylim(min(caida.min() * 1.3, -1), 0)  # deja hueco debajo para la etiqueta
    eje2.margins(x=0)
    peor = caida.idxmin()
    eje2.annotate(f"Máxima: {_num(caida.min(), 1)} %", (peor, caida.min()), xytext=(0, -6),
                  textcoords="offset points", ha="center", va="top", fontsize=9)
    for eje in (eje1, eje2):
        _estilo(eje)
    return figura


def _grafico_riesgo(precios, pesos, valores, ventana, nombre):
    import matplotlib.pyplot as plt

    figura, (eje1, eje2) = plt.subplots(1, 2, figsize=(11, 5), width_ratios=[3, 2], layout="constrained")
    vol = valores.pct_change().rolling(ventana).std() * np.sqrt(DIAS_POR_ANIO) * 100
    eje1.plot(vol.index, vol, color=COLORES[0], linewidth=1.8)
    if vol.notna().any():
        eje1.axhline(vol.mean(), color="#52514e", linestyle="--", linewidth=1,
                     label=f"Media: {_num(vol.mean(), 1)} %")
        eje1.legend(frameon=False)
    eje1.set_ylabel("Volatilidad anualizada (%)")
    eje1.set_title(f"Volatilidad móvil ({ventana} sesiones)", loc="left")
    eje1.set_ylim(bottom=0)
    eje1.margins(x=0)
    eje1.tick_params(axis="x", labelrotation=30)

    riesgo = contribucion_riesgo(precios, pesos) * 100
    orden = riesgo.sort_values().index
    y = np.arange(len(orden))
    eje2.barh(y + 0.2, pesos[orden] * 100, height=0.38, color=COLORES[0], label="Peso")
    eje2.barh(y - 0.2, riesgo[orden], height=0.38, color=COLORES[1], label="Aportación al riesgo")
    eje2.set_yticks(y, orden)
    eje2.set_xlabel("%")
    eje2.set_title("Riesgo aproximado: pesos iniciales", loc="left")
    eje2.legend(frameon=False, loc="lower right")
    for eje in (eje1, eje2):
        _estilo(eje)
    figura.suptitle(f"Riesgo de {nombre}", x=0.01, ha="left", fontweight="bold")
    return figura


def generar_plots(
    precios: pd.DataFrame,
    pesos,
    nombre: str = "Cartera",
    graficos=GRAFICOS,
    benchmark: pd.Series | None = None,
    ventana_volatilidad: int = 63,
    mostrar: bool = True,
    carpeta=None,
) -> dict:
    """Crea los gráficos pedidos y los devuelve como {nombre: figura}.

    graficos: cuáles crear, de entre GRAFICOS.
    ventana_volatilidad: sesiones de la volatilidad móvil (63 = un trimestre).
    carpeta: si se indica, guarda cada gráfico como PNG en ella.
    """
    import matplotlib.pyplot as plt
    from pathlib import Path

    desconocidos = set(graficos) - set(GRAFICOS)
    if desconocidos:
        raise ValueError(f"Gráficos desconocidos: {sorted(desconocidos)}. Opciones: {GRAFICOS}.")
    validar_tabla(precios)
    precios, benchmark, _ = _alinear_benchmark(precios, benchmark)
    if isinstance(ventana_volatilidad, bool) or not isinstance(ventana_volatilidad, int) or ventana_volatilidad < 2:
        raise ValueError("ventana_volatilidad debe ser un entero de al menos 2.")
    pesos = validar_pesos(pesos, precios.columns)
    valores = valor_cartera(precios, pesos)

    constructores = {
        "rendimiento": lambda: _grafico_rendimiento(precios, valores, benchmark, nombre),
        "correlacion": lambda: _grafico_correlacion(precios, nombre),
        "evolucion": lambda: _grafico_evolucion(valores, nombre),
        "riesgo": lambda: _grafico_riesgo(precios, pesos, valores, ventana_volatilidad, nombre),
    }
    figuras = {clave: constructores[clave]() for clave in graficos}
    if carpeta is not None:
        Path(carpeta).mkdir(parents=True, exist_ok=True)
        for clave, figura in figuras.items():
            figura.savefig(Path(carpeta) / f"{clave}.png", dpi=150)
    if mostrar:
        plt.show()
    return figuras
