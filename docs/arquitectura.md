# Arquitectura del toolkit

![Diagrama UML de clases y dependencias](arquitectura.svg)

El rombo vacío representa la agregación de una o varias `SeriePrecios` en
`Cartera`. Una serie existe independientemente y puede utilizarse en varias
carteras. Las flechas discontinuas representan dependencias entre módulos o
clases; las etiquetas indican creación, validación o delegación.

Cómo leer la notación:

| Elemento | Significado |
| --- | --- |
| Línea continua con rombo vacío | Agregación: el rombo está en el todo (`Cartera`); multiplicidades `1..*` (una cartera tiene una o más series) y `0..*` (una serie puede estar en cero o más carteras). |
| Flecha discontinua con punta abierta | Dependencia UML: el origen usa, crea o delega en el destino. Todas corresponden a un `import` real, salvo dos: «crea» de `monte_carlo.py` a `SimulationResult` (la clase está en el mismo fichero) y «consulta opcional», en la que `reportes.py` solo lee el `SimulationResult` que recibe como argumento. |
| `<<dataclass>>` | Clase de datos de Python (`@dataclass`). |
| `<<módulo>>` | Fichero de Python con funciones, no una clase. Se dibuja como caja para mostrar sus dependencias. |
| `+` / `-` | Miembro público / interno (prefijo `_` en Python). |
| `nombre: tipo` | Tipo anotado en el código. `...` indica que se omiten parámetros opcionales. |

No hay herencia entre clases: el diseño se basa en composición y delegación
(véase «Decisiones de diseño» en el README).

## Separación de responsabilidades

- Los adaptadores convierten respuestas externas en `SeriePrecios` o
  `SerieIndicador`. Ambos ofrecen `valores`, `fuente`, `frecuencia` y `unidad`.
- `SeriePrecios.valores` es una propiedad que accede a `precios`, sin duplicarlos.
  Los estadísticos de precios se calculan automáticamente al crear la serie.
- `Cartera` agrupa los activos y pesos y prepara los datos antes de delegar.
  Los indicadores macroeconómicos no se agregan como activos de inversión.
- El motor recibe precios y pesos, sin conocer APIs ni importar `Cartera`.
  Devuelve `SimulationResult`, que reúne escenarios y visualización.
- Los informes reciben datos ya preparados y, opcionalmente, una simulación.
  No importan `Cartera`. Comparten validaciones y alineación con el análisis.

## Flujo del sistema

1. Yahoo, Banco Mundial, FRED o BCE → adaptador → objeto interno normalizado.
2. Series de precios + ponderaciones → `Cartera`.
3. Cartera → validación de frecuencia y moneda → limpieza y fechas comunes.
4. Precios preparados → motor Monte Carlo → `SimulationResult` → trayectorias
   y distribución del valor final.
5. Precios preparados y simulación opcional → informes → Markdown y gráficos
   históricos de rendimiento, correlación, evolución y riesgo.

### Diagrama de secuencia: del dato al informe

El diagrama muestra, en orden temporal, las llamadas reales del caso de uso
principal: descargar acciones de Yahoo, construir la cartera, simularla y
generar el informe. Las flechas continuas son llamadas y las discontinuas,
valores devueltos.

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuario
    participant E as extractores.py
    participant Y as Yahoo Finance
    participant S as SeriePrecios
    participant C as Cartera
    participant L as limpieza.py
    participant M as monte_carlo.py
    participant R as reportes.py

    U->>E: descargar_series(tickers, inicio, fin)
    loop por cada ticker
        E->>Y: Ticker.history(auto_adjust=True)
        Y-->>E: DataFrame con cierres
        E->>S: SeriePrecios(ticker, precios, fuente, moneda)
        Note over S: __post_init__ valida y calcula media y desviación típica
    end
    E-->>U: dict ticker → SeriePrecios

    U->>C: Cartera(nombre, series, pesos)
    Note over C: __post_init__ valida tickers únicos y pesos ≥ 0 que suman 1

    U->>C: monte_carlo(n_sims, horizonte, retorno, volatilidad, nu, v0, semilla)
    C->>C: _preparar_datos(): frecuencia diaria y moneda común
    C->>L: alinear_precios(), validar_tabla(), validar_pesos()
    L-->>C: tabla de fechas comunes y diagnóstico
    C->>M: simular_cartera(tabla, pesos, ...)
    M-->>C: SimulationResult
    C-->>U: SimulationResult con el diagnóstico de limpieza

    U->>C: report(simulacion=resultado, benchmark=...)
    C->>C: _preparar_datos()
    C->>R: generar_report(precios, pesos, simulacion, diagnóstico, monedas)
    R-->>C: texto Markdown
    C-->>U: informe Markdown

    U->>C: plots_report(graficos, benchmark)
    C->>C: _preparar_datos()
    C->>R: generar_plots(precios, pesos, ...)
    R-->>C: figuras de Matplotlib
    C-->>U: dict nombre → figura
```

Puntos que conviene leer en el diagrama:

- **La cartera no calcula, coordina.** `monte_carlo()`, `report()` y
  `plots_report()` pasan por `_preparar_datos()`: simulación, informe y
  gráficos usan exactamente los mismos datos validados y alineados. Después delega en el módulo que sabe
  hacer el cálculo.
- **El motor y los informes no conocen `Cartera` ni las APIs.** Reciben una
  tabla de precios y unos pesos. Por eso se pueden probar con datos sintéticos
  y reutilizar con cualquier fuente.
- **La simulación se pasa al informe, no se recalcula.** `report()` comprueba
  que el `SimulationResult` corresponde a esa cartera y a sus pesos actuales.
- **Para un activo individual** el flujo es más corto:
  `SeriePrecios.monte_carlo()` limpia la serie con `limpiar_precios()` y
  delega en `simular_activo()`. `cartera.monte_carlo(activo="AAPL")` reenvía
  a ese mismo método.

La media y desviación de **precios** se distinguen de la volatilidad y
correlación de **rendimientos** calculadas en el análisis. Los ejemplos guardan
sus salidas en una carpeta excluida de Git.

El [archivo DOT](arquitectura.dot) es la fuente editable del diagrama UML.
El SVG se incluye para que pueda verse directamente en GitHub. Si se desea
regenerarlo con Graphviz (opcional, no necesario para ejecutar el toolkit):

```sh
dot -Tsvg docs/arquitectura.dot -o docs/arquitectura.svg
```

Sin Graphviz instalado, también puede generarse con Node.js mediante
[`@viz-js/viz`](https://www.npmjs.com/package/@viz-js/viz), Graphviz compilado
a WebAssembly. El SVG actual se generó así (Graphviz 16.1.0).
