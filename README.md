<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/img/logo-dark.svg">
  <img src="docs/img/logo-light.svg" alt="portfolio-risk-toolkit" width="600">
</picture>

**Toolkit en Python para descargar datos financieros de varias fuentes, llevarlos a un formato común,
analizar carteras, simular escenarios de Monte Carlo y generar informes, con un dashboard que funciona sin conexión.**

[![CI](https://github.com/raaauulg/portfolio-risk-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/raaauulg/portfolio-risk-toolkit/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776ab.svg)](pyproject.toml)
[![Licencia MIT](https://img.shields.io/badge/licencia-MIT-blue.svg)](LICENSE)
[![Pruebas: pytest sin red](https://img.shields.io/badge/pruebas-pytest%20sin%20red-success.svg)](#pruebas)
[![Abrir en Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://portfolio-risk-toolkit.streamlit.app/?preset=demo)
[![Versión 1.0.0](https://img.shields.io/badge/versi%C3%B3n-1.0.0-informational.svg)](pyproject.toml)

[**Demo en vivo**](https://portfolio-risk-toolkit.streamlit.app/?preset=demo) · [Inicio rápido](#inicio-rápido) · [Uso](#uso-como-librería) · [Dashboard](#dashboard) · [Arquitectura](#arquitectura) · [Funcionamiento](#funcionamiento-en-detalle) · [Hoja de ruta](#hoja-de-ruta) · [Licencia](#licencia)

[English](README.en.md) · **Español**

</div>

portfolio-risk-toolkit nació como trabajo del taller B1-T1 del máster MIAX (Instituto BME): una librería modular en la
que la ingesta de datos está separada del modelado y del análisis. El paquete se instala como `miax-toolkit` y se
importa como `miax_toolkit`.

<p align="center">
  <img src="docs/img/dashboard_resumen.png" alt="Página Resumen del dashboard: seis indicadores de la cartera de demostración frente al S&P 500 y su evolución en base 100" width="100%">
  <br>
  <sub>Cartera de demostración (AAPL, MSFT, JPM, JNJ y XOM, 2021-2025) frente al S&amp;P 500 de FRED, en el
  dashboard y con datos reales guardados en el repositorio. Las métricas y la simulación proceden del toolkit.</sub>
</p>

## Por qué

Los scripts rápidos que descargan precios y calculan cuatro métricas dejan de servir en cuanto hay que combinar
proveedores, mezclar acciones con índices o indicadores macroeconómicos, o repetir el análisis con otra cartera.
portfolio-risk-toolkit resuelve ese problema con un **contrato de datos común**: cada fuente entrega el mismo tipo de objeto,
y la cartera, la limpieza, el motor de simulación y los informes solo dependen de ese contrato. Añadir un
proveedor es escribir un adaptador; el resto del sistema no cambia.

## Funcionalidades

- **Cuatro fuentes, una salida.** Yahoo Finance, Banco Mundial, FRED y BCE devuelven `SeriePrecios` o
  `SerieIndicador` con los mismos atributos (`valores`, `fuente`, `frecuencia`, `unidad`), y `descargar_series`
  descarga listas de activos en lote.
- **DataClasses que se validan.** Series y carteras comprueban sus datos al crearse; las series de precios
  calculan media y desviación típica automáticamente.
- **Limpieza explícita.** Normaliza fechas y valores, descarta lo inválido y alinea calendarios bursátiles
  distintos sin rellenar festivos, con un diagnóstico de lo descartado.
- **Monte Carlo con colas gruesas.** Shocks t de Student multivariantes correlacionados, parametrizables
  (escenarios, horizonte, retorno, volatilidad, grados de libertad, semilla) y aplicables a un activo o a la cartera.
- **Informes en Markdown y gráficos.** `report()` con métricas, diagnósticos y advertencias de riesgo, y
  `plots_report()` con rendimiento, correlación, evolución y riesgo.
- **Dashboard opcional.** Aplicación Streamlit que solo usa la API pública, funciona sin Internet con una
  instantánea de datos reales y no modifica el núcleo.
- **Reproducible y probado.** Semillas fijas, versiones de dependencias fijadas y pruebas que no necesitan red.

## Inicio rápido

Se necesita Python 3.12 y Git. Las versiones de las dependencias están fijadas en [`pyproject.toml`](pyproject.toml).

```powershell
git clone https://github.com/raaauulg/portfolio-risk-toolkit.git
cd portfolio-risk-toolkit
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\python.exe ejemplos/demo_completa.py
```

En macOS o Linux, el entorno se crea con `python3.12 -m venv .venv` y el intérprete es `.venv/bin/python`. No hace
falta activar el entorno.

La demostración usa datos sintéticos con semilla fija, así que no necesita conexión y su salida es siempre la misma:

```text
ACC_A: media de precios=121.54, desviación de precios=29.09
ACC_B: media de precios=106.03, desviación de precios=12.37
BONO_C: media de precios=110.65, desviación de precios=4.49
Cartera sintética, a 252 días de mercado, partiendo de 100.00:
- Percentil 5 del valor final (P5): 78.06.
- Mediana del valor final (P50): 106.77.
- Percentil 95 del valor final (P95): 154.46.
...
Informe y cinco gráficos guardados en ...\portfolio-risk-toolkit\resultados\demo
```

Para abrir el dashboard:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[app]"
.\.venv\Scripts\python.exe -m streamlit run app/dashboard.py
```

Se abre en <http://localhost:8501>; con <http://localhost:8501/?preset=demo> arranca con la cartera de demostración
ya calculada.

| Extra | Instalación | Para qué |
| --- | --- | --- |
| — | `pip install .` | El toolkit. |
| `dev` | `pip install -e ".[dev]"` | Pruebas con pytest. |
| `app` | `pip install -e ".[app]"` | Dashboard (Streamlit y Plotly). |

## Uso como librería

```python
from miax_toolkit import Cartera, descargar_series, descargar_sp500_fred

datos = descargar_series(["AAPL", "MSFT"], "2025-01-01", "2026-01-01")
cartera = Cartera("Acciones USA", list(datos.values()), {"AAPL": 0.6, "MSFT": 0.4})
referencia = descargar_sp500_fred("2025-01-01", "2026-01-01")

resultado = cartera.monte_carlo(n_sims=2000, horizonte=252, retorno=0.06, volatilidad=None,
                                nu=5, v0=100.0, semilla=42)
print(resultado.interpretacion())
resultado.plot()

print(cartera.report(simulacion=resultado, benchmark=referencia.valores))
cartera.plots_report(benchmark=referencia.valores)

# Un activo individual parte de su último precio, salvo que se indique v0.
individual = datos["AAPL"].monte_carlo(n_sims=1000, horizonte=126)
```

Con la cartera de demostración (calibrada con 2021-2025, 5.000 escenarios a 252 sesiones y `nu = 5`),
`resultado.plot()` dibuja el abanico de trayectorias y la distribución del valor final:

<p align="center">
  <img src="docs/img/toolkit_monte_carlo.png" alt="Trayectorias simuladas con bandas P5-P95 y P25-P75 y mediana, e histograma del valor final con P5, P50 y P95" width="100%">
</p>

`report()` devuelve Markdown listo para guardar o publicar. Extracto real con la misma cartera frente al S&P 500:

```markdown
# Informe de Cartera Demo (EE. UU.)

Periodo: 04/01/2021 a 31/12/2025 (1255 sesiones). Cartera de comprar y mantener.

| Métrica | Valor |
| --- | --- |
| Rentabilidad anualizada | 19,46 % |
| Volatilidad anualizada | 16,21 % |
| Ratio de Sharpe (tasa libre 0,00 %) | 1,18 |
| Caída máxima | -17,37 % |
| VaR diario histórico al 95 % | 1,61 % |
| CVaR diario histórico al 95 % | 2,29 % |
| Beta frente a ^GSPC | 0,83 |
```

Y `plots_report()` devuelve las figuras analíticas como un diccionario de figuras de Matplotlib:

| Evolución y caídas desde máximos | Correlación de rendimientos |
| :---: | :---: |
| <img src="docs/img/toolkit_evolucion.png" alt="Evolución del valor de la cartera en base 100 y caídas desde máximos" width="100%"> | <img src="docs/img/toolkit_correlacion.png" alt="Matriz de correlación de rendimientos diarios" width="100%"> |

<p align="center">
  <img src="docs/img/toolkit_riesgo.png" alt="Volatilidad móvil a 63 sesiones y peso frente a aportación al riesgo por activo" width="100%">
</p>

Los scripts de [`ejemplos/`](ejemplos) recorren el toolkit completo:

| Script | Qué muestra | Red |
| --- | --- | --- |
| [`demo_completa.py`](ejemplos/demo_completa.py) | DataClasses, estadísticos, cartera, limpieza, Monte Carlo individual y conjunto, informe y gráficos, con datos sintéticos. | No |
| [`demo_fuentes.py`](ejemplos/demo_fuentes.py) | Las cuatro fuentes y el análisis completo de AAPL y MSFT frente al S&P 500. | Sí |

Cada script escribe `informe.md` y cinco imágenes en `resultados/demo` o `resultados/fuentes` (`--salida` cambia el
destino). Los resultados no se versionan.

## Dashboard

**[Abrir la demo en vivo →](https://portfolio-risk-toolkit.streamlit.app/?preset=demo)**

Aplicación Streamlit para explorar el toolkit sin escribir código. Es un consumidor más de la API pública,
como los scripts de `ejemplos/`, y no modifica `src/`; sus dependencias son opcionales y `import miax_toolkit` no
carga Streamlit ni Plotly.

- **Dos modos de datos.** *Instantánea*, por defecto, usa los precios reales de 2021-2025 guardados en
  [`data/sample/`](data/sample) y funciona sin Internet. *En directo* descarga de Yahoo Finance y FRED.
- **Tres presets.** Cinco empresas de distintos sectores de EE. UU. frente al S&P 500, tecnológicas de EE. UU. y una
  cartera europea en EUR. Cada uno usa una sola moneda, porque el toolkit no convierte divisas.
- **Las cifras y las validaciones son las del toolkit.** Unos pesos que no suman 100 % o una cartera con varias
  monedas muestran el mensaje de su `ValueError`, y un fallo de red se distingue de una consulta sin datos.

<table>
  <tr>
    <td width="50%"><img src="docs/img/dashboard_datos.png" alt="Página Datos y calidad con la cartera europea"></td>
    <td width="50%"><img src="docs/img/dashboard_riesgo.png" alt="Página Cartera y riesgo: composición, peso frente a aportación al riesgo y métricas por activo"></td>
  </tr>
  <tr>
    <td><sub><b>Datos y calidad.</b> Contrato de datos de cada serie y diagnóstico de limpieza y alineación; aquí,
    la cartera europea con tres bolsas y calendarios distintos.</sub></td>
    <td><sub><b>Cartera y riesgo.</b> Composición, peso frente a aportación al riesgo y métricas por activo.</sub></td>
  </tr>
  <tr>
    <td><img src="docs/img/dashboard_riesgo_caidas.png" alt="Caídas desde máximos, volatilidad móvil y distribución de rendimientos"></td>
    <td><img src="docs/img/dashboard_monte_carlo.png" alt="Página Monte Carlo: probabilidad de pérdida, percentiles, abanico de escenarios e histograma"></td>
  </tr>
  <tr>
    <td><sub><b>Caídas y volatilidad.</b> Caídas desde máximos, volatilidad móvil y rendimientos diarios con VaR y
    CVaR.</sub></td>
    <td><sub><b>Monte Carlo.</b> Probabilidad de pérdida, percentiles, abanico de escenarios y valor final.</sub></td>
  </tr>
  <tr>
    <td><img src="docs/img/dashboard_colas.png" alt="Comparador de colas: la misma cartera con nu = 5 y nu = 200"></td>
    <td><img src="docs/img/dashboard_informe.png" alt="Página Informe con la salida de report()"></td>
  </tr>
  <tr>
    <td><sub><b>Comparador de colas.</b> La misma cartera y semilla con <code>nu = 5</code> y con
    <code>nu = 200</code> (casi normal), día a día.</sub></td>
    <td><sub><b>Informe.</b> La salida de <code>report()</code> sin modificar, con descarga en Markdown, y las
    figuras de <code>plots_report()</code>.</sub></td>
  </tr>
  <tr>
    <td><img src="docs/img/dashboard_arquitectura.png" alt="Página Arquitectura con los diagramas del toolkit"></td>
    <td><img src="docs/img/dashboard_error.png" alt="Aviso de consulta sin datos en modo En directo"></td>
  </tr>
  <tr>
    <td><sub><b>Arquitectura.</b> Diagramas de clases y de secuencia, y las funciones públicas que usa la
    aplicación, generadas a partir de sus imports.</sub></td>
    <td><sub><b>Errores.</b> Un ticker inexistente en modo <i>En directo</i> produce un aviso de consulta sin datos,
    distinto del de fallo de conexión.</sub></td>
  </tr>
</table>

## Arquitectura

<p align="center">
  <img src="docs/arquitectura.svg" alt="Diagrama UML de clases y dependencias del toolkit" width="100%">
</p>

Las flechas discontinuas significan «usa, crea o delega en» y el rombo vacío indica que una `Cartera` agrega una o
más `SeriePrecios`. [docs/arquitectura.md](docs/arquitectura.md) explica la notación y añade un diagrama de
secuencia del flujo completo, desde la descarga hasta el informe.

| Módulo | Responsabilidad |
| --- | --- |
| `extractores.py` | Yahoo Finance y descarga por lotes |
| `macroeconomia.py` | `SerieIndicador` y Banco Mundial |
| `fuentes.py` | FRED y BCE |
| `modelos.py` | `SeriePrecios` |
| `cartera.py` | `Cartera`: valida, prepara los datos y delega los cálculos |
| `limpieza.py` | Limpieza, alineación y validación |
| `monte_carlo.py` | Motor de simulación y `SimulationResult` |
| `reportes.py` | Informe en Markdown, métricas y gráficos |
| `app/` | Dashboard (capa de presentación, fuera del paquete) |

### Decisiones de diseño

- **DataClasses que se validan al crearse.** `SeriePrecios`, `SerieIndicador`, `Cartera` y `SimulationResult`
  comprueban sus requisitos en `__post_init__`; los controles propios del análisis (frecuencia, moneda y precios
  limpios) se repiten antes de cada cálculo, porque los objetos son mutables.
- **Composición y delegación en lugar de herencia.** `Cartera` agrega `SeriePrecios`, y `monte_carlo()`,
  `report()` y `plots_report()` preparan los datos y delegan en módulos de funciones que trabajan con tablas de
  pandas y no conocen ni `Cartera` ni las APIs. Cada cálculo se prueba con datos sintéticos, y el mismo motor sirve
  para un activo y para una cartera.
- **Dos clases de series independientes.** Un indicador macroeconómico no es un precio y no debe entrar en una
  cartera; `Cartera` comprueba que sus activos sean `SeriePrecios`.
- **Errores explícitos antes que correcciones silenciosas.** Lo que no cumple las restricciones se rechaza con un
  mensaje claro. Los adaptadores lanzan `RuntimeError` ante fallos de red o del proveedor y `ValueError` cuando no
  hay datos o la entrada no es válida.
- **t de Student multivariante.** Colas más gruesas que la normal, con la correlación entre activos mantenida
  mediante el factor de Cholesky y un mismo chi-cuadrado para todos los activos en cada día.

## Funcionamiento en detalle

### Fuentes de datos

| Fuente | Funciones | Salida |
| --- | --- | --- |
| Yahoo Finance (`yfinance`) | `descargar_serie`, `descargar_series` | Cierres diarios de acciones e índices como `SeriePrecios`. |
| Banco Mundial (API de indicadores) | `descargar_indicador` | Indicadores anuales por país como `SerieIndicador`. |
| FRED (descarga pública en CSV) | `descargar_sp500_fred`, `descargar_indicador_fred` | S&P 500 como `SeriePrecios`; indicadores como `SerieIndicador`. |
| BCE (API SDMX) | `descargar_tipo_cambio_bce` | Tipo de referencia diario, en unidades de la moneda por 1 EUR, como `SerieIndicador`. |

Todas las salidas comparten `valores` (una `pandas.Series` numérica con `DatetimeIndex` ordenado), `fuente`,
`frecuencia` y `unidad`, y conservan sus metadatos propios: ticker, moneda y ajuste en los precios; indicador y país
o área en los indicadores. En `SeriePrecios`, `valores` es una propiedad que devuelve `precios` sin duplicarlos. Un
mismo tipo de dato devuelve la misma clase sea cual sea el proveedor: el S&P 500 de Yahoo y el de FRED son
`SeriePrecios` con el identificador `^GSPC`.

```python
from miax_toolkit import descargar_indicador, descargar_indicador_fred, descargar_tipo_cambio_bce

pib = descargar_indicador("ESP", "NY.GDP.MKTP.CD", 2020, 2024)
paro = descargar_indicador_fred("UNRATE", "2025-01-01", "2026-01-01",
                                pais="USA", frecuencia="mensual", unidad="%")
eurusd = descargar_tipo_cambio_bce("USD", "2025-01-01", "2025-02-01")
```

<details>
<summary><b>Detalles por proveedor</b></summary>

- Yahoo descarga cierres ajustados por dividendos y splits (`auto_adjust=True`). En índices de precios como el
  S&P 500 eso no equivale a un índice de rentabilidad total; el campo `ajuste` distingue ambos casos.
- La moneda indicada al descargar tiene prioridad. Si no se indica, se toma de los metadatos de Yahoo y, en su
  defecto, de `fast_info`. Si no se conoce, queda `None`: la serie se puede consultar, pero hay que completar la
  moneda antes de usarla en una cartera. Indicar una moneda no convierte precios.
- `descargar_series` procesa la lista de forma secuencial, rechaza tickers repetidos y se detiene en el primer fallo
  para no devolver una cartera incompleta sin avisar.
- Yahoo, FRED y BCE reciben fechas `AAAA-MM-DD`, con inicio inclusivo y fin exclusivo. Banco Mundial recibe años con
  ambos extremos inclusivos y fecha cada dato anual el 31 de diciembre.
- El CSV de FRED no trae metadatos suficientes, así que para sus indicadores se indican país, frecuencia y unidad
  según la ficha de la serie. Es la descarga pública, no la API con clave. El S&P 500 de FRED cubre una ventana
  móvil de diez años y se devuelve el periodo realmente disponible.
- Banco Mundial identifica el PIB `NY.GDP.MKTP.CD` como USD corrientes; para otros indicadores se puede indicar
  `unidad` y, si no, queda `no especificada`.
- Los huecos de los indicadores se omiten: no se interpolan, no se cambia la frecuencia ni se rellenan
  observaciones.
- Las consultas reales usan fechas fijas, pero los proveedores pueden revisar sus datos. Un fallo de descarga
  produce un error explícito: nunca se sustituyen datos reales por sintéticos.

</details>

### Cartera, limpieza y validación de entradas

`SeriePrecios` calcula al crearse la media y la desviación típica muestral (`ddof=1`) de los precios válidos. Son
estadísticos de niveles de precio, no de rentabilidades; si se modifica la serie, hay que crear un objeto nuevo
para recalcularlos.

`Cartera` agrupa series y pesos por ticker. Exige activos únicos, un peso por activo y pesos finitos, no negativos
y que sumen uno con tolerancia `1e-6`; dentro de esa tolerancia los normaliza para invertir exactamente el capital
inicial. La composición se vuelve a validar antes de cada análisis por si se han editado los activos o los pesos.

La entrada se restringe a propósito: el análisis trabaja con **precios diarios** positivos y finitos, con fechas
únicas y en **una sola moneda conocida**. Se prefiere rechazar un dato ambiguo antes que interpretarlo en silencio.

<details>
<summary><b>Reglas de limpieza y mínimos de datos</b></summary>

- No se aceptan datos intradía, semanales o mensuales como si fueran diarios, ni posiciones cortas, ni carteras
  con varias monedas.
- Una serie puede crearse con huecos, que se eliminan en la limpieza antes del análisis. Necesita al menos dos
  valores finitos para sus estadísticos.
- `limpiar_precios` recibe una `Series`: normaliza las fechas, elimina `NaT`, ordena, conserva el último registro de
  cada fecha duplicada, convierte textos numéricos con coma decimal y descarta valores ausentes, infinitos o no
  positivos. Reconoce fechas `AAAA-MM-DD` y `DD-MM-AAAA` con separadores `-`, `/` o `.`, y elimina la zona horaria
  conservando la fecha local de la sesión. Avisa de huecos abundantes y de saltos grandes, pero no corrige splits.
  Rechaza varios instantes distintos de una misma sesión, porque convertir datos intradía en cierres diarios es una
  decisión que corresponde al usuario. Los booleanos y los números complejos no se interpretan como precios.
- `alinear_precios` recibe un diccionario de series o un DataFrame, conserva solo las fechas con precio válido para
  todos los activos, sin rellenar festivos, y devuelve la tabla junto con un diagnóstico de lo descartado.
- Los informes necesitan al menos tres fechas comunes. Monte Carlo exige 30 por defecto; `min_observaciones`
  permite bajarlo hasta tres. Es un umbral de diseño, no una garantía estadística. Los informes avisan cuando hay
  menos de un año de historia.
- El benchmark se limpia y se cruza por fechas reales con la cartera; el informe y los gráficos históricos se
  calculan sobre ese periodo común, que debe tener al menos tres fechas. El benchmark no se rellena con precios
  pasados.
- `simular_cartera` y `simular_activo` reciben precios ya limpios y sin metadatos, así que quien las llama debe
  garantizar la moneda común y la frecuencia diaria. Los métodos de los objetos son la entrada recomendada.

</details>

### Monte Carlo

| Parámetro | Significado |
| --- | --- |
| `n_sims` | Número de escenarios. |
| `horizonte` | Sesiones simuladas. |
| `retorno`, `volatilidad` | Anuales. `None` los estima del histórico; un número los fija para todos los activos; un diccionario los cambia por activo. |
| `nu` | Grados de libertad de la t de Student (`nu > 2`). |
| `v0` | Capital inicial. |
| `semilla` | Reproducibilidad. |

El modelo usa rendimientos logarítmicos diarios `r = retorno/252 + volatilidad/sqrt(252) · Z`, con shocks t
multivariantes estandarizados (media cero, varianza uno), y aplica `P(t+1) = P(t) · exp(r)`. `retorno` es por tanto
logarítmico, no una rentabilidad simple esperada. La correlación se estima con el histórico y los shocks se generan
correlacionados. La cartera es de comprar y mantener: pesos iniciales y sin rebalanceos.

`SimulationResult` incluye las trayectorias, P5/P50/P95, la media muestral y la probabilidad de terminar por debajo
del capital inicial, además del periodo de calibración. Con shocks t exponenciados la esperanza teórica del precio
no es finita, así que **se interpretan la mediana y los percentiles, no la media**. Son escenarios con parámetros
constantes, no predicciones.

<details>
<summary><b>Casos particulares del modelo</b></summary>

- Todos los parámetros deben ser finitos; los valores numéricos no válidos se rechazan expresamente.
- Una matriz con correlaciones perfectas se admite mediante su descomposición espectral.
- Un activo constante conserva volatilidad histórica cero. Si se le impone una volatilidad positiva, se usa
  correlación cero con los demás porque el histórico no permite estimarla; aun así no es independiente, ya que todos
  los shocks comparten el factor chi-cuadrado de la t multivariante.
- El histograma recorta a P1–P99 para facilitar la lectura (si el recorte lo dejara vacío, muestra todos los
  escenarios y lo indica en el título); los percentiles y resúmenes usan siempre todos los escenarios.
- Con poca historia, la estimación del retorno es inestable. No se modelan costes, impuestos, rebalanceos ni cambios
  futuros de volatilidad o correlación.

</details>

### Informes y gráficos

`cartera.report()` devuelve Markdown y admite `secciones`, `tasa_libre` anual, `nivel_var`, `benchmark`,
`simulacion`, `umbrales` y `ruta` para guardar el texto. Las secciones disponibles son `resumen`, `composicion`,
`activos`, `correlaciones`, `montecarlo`, `diagnostico` y `advertencias`:

```python
texto = cartera.report(secciones=("resumen", "advertencias"), nivel_var=0.99)
```

Incluye rentabilidad total y anualizada, volatilidad, Sharpe, Sortino, caída máxima, VaR y CVaR históricos y, si
hay una referencia con variación suficiente, la beta. VaR y CVaR se expresan como pérdidas diarias. Las métricas que
no se pueden estimar aparecen como `n/d`, y los umbrales de las advertencias son configurables.

`cartera.plots_report()` permite elegir `graficos` (`rendimiento`, `correlacion`, `evolucion`, `riesgo`) y configurar
`ventana_volatilidad`, `benchmark`, `mostrar` y `carpeta`.

<details>
<summary><b>Convenciones de las métricas</b></summary>

- La anualización supone 252 observaciones por año. Después de alinear, un rendimiento puede abarcar más de una
  sesión; el toolkit no reconstruye ese calendario, así que con muchos huecos la anualización es solo aproximada.
- VaR y CVaR pueden ser negativos si incluso los peores rendimientos fueron positivos.
- La aportación al riesgo se calcula con los pesos iniciales fijos, que no coinciden con la evolución real de los
  pesos en comprar y mantener.
- La valoración histórica parte de base 100.
- Una simulación incluida en el informe conserva su capital, sus supuestos y su periodo de calibración, que el
  informe muestra por separado; añadir un benchmark no la recalibra.
- Si no hay sesiones suficientes para la ventana de volatilidad, no se inventan observaciones.

</details>

### Cómo añadir una fuente de datos

Basta con un adaptador que cumpla el contrato; la cartera, la limpieza, el motor y los informes no cambian.

1. Escribir la función de descarga en un módulo de ingesta, por ejemplo `fuentes.py`, que ya ofrece `_intervalo`,
   `_csv` y `_normalizar`. Debe lanzar `RuntimeError` si falla la red y `ValueError` si los datos no son válidos.
2. Normalizar la respuesta al contrato: `Series` de `float` con índice de fechas sin zona horaria, ordenado y sin
   duplicados.
3. Devolver `SeriePrecios` si son precios (con `moneda` y `ajuste`) o `SerieIndicador` en otro caso.
4. Exportarla en `src/miax_toolkit/__init__.py` y en `__all__`.
5. Probarla sin Internet, simulando la llamada de red con `unittest.mock.patch`.

```python
# src/miax_toolkit/fuentes.py (la URL es ficticia)
def descargar_precios_mi_proveedor(ticker: str, inicio: str, fin: str, moneda: str) -> SeriePrecios:
    """Cierres diarios de Mi Proveedor normalizados al contrato común."""
    primero, ultimo = _intervalo(inicio, fin)
    tabla = _csv("https://proveedor.example/precios.csv", {"s": ticker}, "Mi Proveedor")
    precios = _normalizar(tabla, "Date", "Close", primero, ultimo, ticker.upper())
    return SeriePrecios(ticker.upper(), precios, "Mi Proveedor", moneda=moneda, ajuste="no_especificado")
```

A partir de ahí, la serie se usa igual que una de Yahoo:
`Cartera("Mixta", [serie_yahoo, serie_nueva], pesos).report()`.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,app]"
.\.venv\Scripts\python.exe -W error -m pytest -q
```

La [integración continua](.github/workflows/ci.yml) las ejecuta en cada push y pull request, en Ubuntu y en Windows,
junto con la demostración sin conexión y una instalación del núcleo sin las dependencias del dashboard.

Las pruebas no necesitan Internet: las llamadas a Yahoo, Banco Mundial, FRED y BCE se simulan con `unittest.mock`
y el resto usa datos sintéticos con semilla fija. Comprueban, entre otras cosas, que todas las fuentes cumplen el
mismo contrato, que la cartera valida pesos, moneda y frecuencia, que la simulación es reproducible y que la mediana
de `log(valor final)` coincide con `log(v0) + retorno · años`. Las del dashboard (`tests/app/`, con
`streamlit.testing.v1.AppTest`) recorren los tres presets sin conexión, comprueban los errores de consulta, pesos y
monedas, y verifican que las cifras mostradas coinciden con las del informe del toolkit; se omiten si no está
instalado el extra `app`.

## Limitaciones

- No se convierten divisas: una cartera con varias monedas se rechaza.
- La anualización supone 252 sesiones por año y es aproximada si la historia tiene muchos huecos.
- Monte Carlo usa parámetros constantes y no modela costes, impuestos ni rebalanceos.
- `descargar_series` descarga en serie y se detiene en el primer fallo: no paraleliza ni devuelve resultados
  parciales.
- El contrato común de las series es una convención y los adaptadores son funciones, no un `typing.Protocol` ni una
  clase abstracta. Con cuatro fuentes basta; con más convendría formalizarlo.
- El dashboard deriva en `app/transformaciones.py` tres series que la API pública no expone (caídas, volatilidad
  móvil y rendimientos diarios), con pruebas que comprueban que coinciden con las figuras del toolkit.
- Los activos de la instantánea se eligieron a posteriori entre grandes compañías actuales (sesgo de
  supervivencia), así que su rentabilidad histórica es optimista.

## Hoja de ruta

**Dashboard como servicio propio.** La [demo pública](https://portfolio-risk-toolkit.streamlit.app/?preset=demo) se
sirve desde Streamlit Community Cloud, que instala el proyecto con `requirements.txt`. Para un servicio con control total sobre recursos y acceso:

1. **Contenedor.** `Dockerfile` con Python 3.12 que instale `.[app]` y arranque Streamlit con
   `--server.address 0.0.0.0 --server.headless true`, con `HEALTHCHECK` sobre `/_stcore/health`. La instantánea va
   dentro de la imagen, así que el servicio no depende de Yahoo ni de FRED para arrancar.
2. **Servidor.** Una máquina virtual pequeña (Azure, AWS o GCP) con el contenedor en reinicio automático
   (`--restart unless-stopped` o systemd), o un servicio gestionado como Azure Container Apps o Google Cloud Run.
3. **Acceso.** Proxy inverso (nginx o Caddy) con HTTPS y, si se publican datos con condiciones de uso
   restrictivas, autenticación.
4. **Datos al día.** Tarea programada (cron o GitHub Actions) que ejecute `python -m app.generar_instantanea`,
   pase las pruebas y publique la nueva instantánea, y caché persistente de descargas en Parquet o SQLite.
5. **Varios usuarios.** Límites de memoria y escenarios por sesión, y simulaciones grandes en un proceso aparte.

**Toolkit.**

- Análisis estático (`ruff` y `mypy`) en la integración continua, que hoy ejecuta las pruebas en Ubuntu y Windows.
- Contrato formal de adaptadores con `typing.Protocol` o una clase abstracta.
- Funciones públicas en `reportes` para caídas, volatilidad móvil, beta y advertencias como datos, de modo que el
  dashboard deje de necesitar `app/transformaciones.py`.
- Descargas en paralelo con reintentos y espera exponencial, y nuevas fuentes (Alpha Vantage, Finnhub, fundamentales).
- Carteras multimoneda con el tipo de cambio de `descargar_tipo_cambio_bce`.
- Rebalanceo periódico y costes de transacción.
- Volatilidad variable (GARCH), correlaciones dinámicas y *bootstrap* histórico como alternativas a la t de Student.
- Backtesting *walk-forward* y optimización de pesos (mínima varianza, paridad de riesgo).
- En el dashboard: comparación de varias carteras, exportación del informe a PDF y revisión del tema oscuro.

## Documentación

| Documento | Contenido |
| --- | --- |
| [Arquitectura](docs/arquitectura.md) | Notación UML, separación de responsabilidades y diagrama de secuencia |
| [Datos de la instantánea](data/sample/README.md) | Fuentes, fecha de descarga, formato, ajuste, sesgo de supervivencia y condiciones de uso |
| [Ejemplos](ejemplos) | Scripts reproducibles del toolkit completo y de las cuatro fuentes |

<details>
<summary><b>Correspondencia con el enunciado del taller</b></summary>

| Apartado | Dónde está |
| --- | --- |
| 4.1 Repositorio y despliegue | Este README, `src/`, `pyproject.toml`, `.gitignore` |
| 4.2 Ingesta multifuente | `extractores.py`, `macroeconomia.py`, `fuentes.py`; descarga en lote con `descargar_series` |
| 4.3 Series de precios y cartera | `modelos.py`, `cartera.py` |
| 4.4 Monte Carlo | `monte_carlo.py`, `Cartera.monte_carlo()`, `SimulationResult.plot()` |
| 4.5 Limpieza, validación y reportes | `limpieza.py`, `reportes.py`, `Cartera.report()`, `Cartera.plots_report()` |
| 4.6 Diagramas | `docs/arquitectura.md`, `docs/arquitectura.svg`, `docs/secuencia.svg` |

</details>

<details>
<summary><b>Referencias</b></summary>

- [yfinance: consulta de históricos](https://ranaroussi.github.io/yfinance/reference/api/yfinance.Ticker.history.html).
- [Banco Mundial: API de indicadores](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation).
- [FRED: descarga de datos](https://fred.stlouisfed.org/help/data/downloading/using-the-download-data-link/),
  [ficha de UNRATE](https://fred.stlouisfed.org/series/UNRATE) y [ficha de SP500](https://fred.stlouisfed.org/series/SP500).
- [BCE: ejemplos de la API SDMX](https://data.ecb.europa.eu/help/api/data-examples).
- [Distribución t multivariante](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.multivariate_t.html)
  (referencia matemática; el motor está implementado con NumPy y no requiere SciPy).

</details>

## Licencia

El código se distribuye bajo la [licencia MIT](LICENSE): se puede usar, modificar y redistribuir libremente,
también con fines comerciales, conservando el aviso de copyright.

Los datos de [`data/sample/`](data/sample) no están cubiertos por esa licencia: proceden de Yahoo Finance y FRED y
mantienen las condiciones de uso de sus proveedores (el S&P 500 es propiedad de S&P Dow Jones Indices), descritas en
[su README](data/sample/README.md).

portfolio-risk-toolkit es una herramienta académica de análisis: sus resultados son históricos o simulados y nada de lo que
contiene es asesoramiento financiero.

## Autores

Javier Hernández Olba · Raúl Gómez Amat · Amalia Lobo Barce

Taller B1-T1 del máster MIAX, Instituto BME, 2026.
