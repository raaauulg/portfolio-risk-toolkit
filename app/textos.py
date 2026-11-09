"""Textos de ayuda, glosario y explicaciones, escritos para alguien de finanzas que no programa."""

AYUDA = {
    "modo": "Instantánea: datos reales guardados en el repositorio (descargados el 09/11/2026); "
            "funciona sin Internet. En directo: descarga de Yahoo Finance y FRED con el toolkit.",
    "activos": "Hasta 8 activos de una sola moneda. El toolkit no convierte divisas y rechaza "
               "carteras que las mezclan.",
    "tickers": "Acciones e índices de Yahoo Finance separados por comas, por ejemplo: AAPL, MSFT, ^GSPC. "
               "Los índices se reconocen por el prefijo ^ de Yahoo. "
               "Los símbolos repetidos se consideran una sola vez, sin distinguir mayúsculas.",
    "desde": "Primera fecha del análisis (incluida).",
    "hasta": "Última fecha del análisis (incluida).",
    "benchmark": "Índice de referencia para comparar la cartera. Las métricas se calculan sobre "
                 "las fechas con datos disponibles de la cartera y del índice, sin rellenar huecos.",
    "pesos": "Peso inicial de cada activo, en %. Deben sumar 100 %. La cartera es de comprar y "
             "mantener: se invierte el primer día y no se rebalancea.",
    "n_sims": "Número de escenarios simulados. Más escenarios dan percentiles más estables, "
              "pero tardan más (máximo 20.000).",
    "horizonte": "Sesiones bursátiles simuladas hacia delante (252 ≈ un año).",
    "retorno": "Retorno logarítmico anual de cada activo. Histórico: el estimado con los datos "
               "elegidos. Supuesto propio: el mismo valor para todos los activos.",
    "volatilidad": "Volatilidad anual de cada activo. Histórica: la estimada con los datos "
                   "elegidos. Supuesto propio: la misma para todos los activos.",
    "nu": "Grados de libertad de la t de Student (mayor que 2). Cuanto menor, colas más gruesas: "
          "más escenarios extremos. Con valores altos (> 30) se parece a una normal.",
    "semilla": "Fija los números aleatorios: con la misma semilla se obtienen exactamente los mismos escenarios.",
    "v0": "Capital inicial de la simulación, en la moneda de la cartera.",
    "tasa_libre": "Tipo libre de riesgo anual para el ratio de Sharpe y el de Sortino. Con 0 % "
                  "(valor por defecto del toolkit) el Sharpe es mayor que con el tipo real de las "
                  "letras del Tesoro.",
    "nivel_var": "Nivel de confianza del VaR y el CVaR históricos diarios.",
    "calcular": "Aplica la configuración: descarga o lee los datos, construye la cartera, "
                "la simula y genera el informe. Los resultados quedan en caché.",
}

GLOSARIO = {
    "Rentabilidad anualizada": "Crecimiento medio por año que habría dado la misma rentabilidad "
                               "total, con 252 sesiones por año.",
    "Volatilidad anualizada": "Desviación típica de las rentabilidades diarias multiplicada por "
                              "√252. Mide cuánto oscila la cartera; no distingue subidas de bajadas.",
    "Ratio de Sharpe": "Rentabilidad media anual por encima del tipo libre de riesgo, dividida "
                       "por la volatilidad. Rentabilidad obtenida por cada unidad de riesgo.",
    "Caída máxima (drawdown)": "Mayor pérdida desde un máximo previo hasta un mínimo posterior. "
                               "Lo peor que habría vivido quien compró en el peor momento.",
    "VaR histórico": "Umbral de pérdida diaria estimado con los rendimientos históricos. Al 95 %, "
                     "delimita aproximadamente el 5 % de los peores días. Puede ser negativo si "
                     "incluso esos rendimientos fueron positivos.",
    "CVaR histórico": "Pérdida media de los días que alcanzan o superan el VaR. Resume la "
                      "gravedad de la cola de pérdidas históricas.",
    "t de Student": "Distribución parecida a la normal pero con colas más gruesas: los movimientos "
                    "extremos son más probables, como en los mercados reales.",
    "nu (grados de libertad)": "Controla el grosor de las colas de la t de Student. Con nu = 5 "
                               "hay bastantes más extremos que con una normal; con nu alto se "
                               "parece a la normal.",
    "Percentiles (P5, P50, P95)": "P5: el 5 % de los escenarios termina por debajo. P50 "
                                  "(mediana): la mitad termina por encima. P95: solo el 5 % lo "
                                  "supera. Se usan en lugar de la media porque con colas t la "
                                  "media de los escenarios es inestable.",
    "Aportación al riesgo": "Parte de la varianza de la cartera que se debe a cada activo, con "
                            "los pesos iniciales. Un activo puede pesar poco y aportar mucho riesgo.",
}

AVISO_MONTE_CARLO = ("Son **escenarios** posibles bajo supuestos constantes, **no predicciones**. "
                     "Se interpretan la **mediana** y los **percentiles**, no la media.")

ESTADO_VACIO = ("Elige un preset en la barra lateral (por ejemplo, **Demo de la presentación**) "
                "o configura los tres pasos y pulsa **Calcular**.")

ARQUITECTURA = [
    "El toolkit separa capas: los adaptadores crean `SeriePrecios` o `SerieIndicador` según "
    "el dato. La `Cartera` agrupa precios, valida y delega; los módulos de limpieza, Monte Carlo "
    "e informes hacen los cálculos sin conocer ni las APIs ni la cartera.",
    "Este dashboard es una capa de presentación más: un consumidor de la API pública del "
    "toolkit, igual que los scripts de `ejemplos/`. Las métricas, los informes y las simulaciones "
    "proceden del núcleo; `app/transformaciones.py` deriva las series auxiliares para dibujar.",
    "**Este dashboard no modifica ni una línea de `src/`.** Se añadió como un paquete "
    "aparte (`app/`) con dependencias opcionales (`pip install -e \".[app]\"`); "
    "`import miax_toolkit` no carga Streamlit ni Plotly.",
    "Las validaciones también son del toolkit: si unos pesos no suman 100 % o la cartera "
    "mezcla monedas, el aviso que se ve es el mensaje del propio `ValueError`.",
    "Un nuevo adaptador de precios que cumpla el contrato de `SeriePrecios` se puede usar sin "
    "cambiar la cartera, el motor ni los informes. Para ofrecerlo en el dashboard también habría "
    "que incorporarlo a su carga de datos y sus controles.",
]
