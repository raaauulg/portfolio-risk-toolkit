# MIAX — Taller B1-T1

Proyecto académico en Python para la extracción de información bursátil, el
modelado de series de precios y la gestión de carteras de inversión.

## Requisitos

- Python 3.12 o superior.
- Git, y conexión a Internet para instalar dependencias o consultar las APIs.
- Acceso al repositorio privado de GitHub.

## Instalación en Windows

Abrir una terminal en la carpeta donde se quiera descargar el proyecto:

```powershell
git clone https://github.com/JaviHdezOlba/miax-b1-t1.git
cd miax-b1-t1
git fetch origin
git switch feat/bloques-4-1-4-3
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Si el repositorio ya está clonado, **no repetir** `git clone`. Antes de cambiar
de rama, guardar los cambios locales pendientes. Después, desde la carpeta
del proyecto:

```powershell
git fetch origin
git switch feat/bloques-4-1-4-3
git pull --ff-only origin feat/bloques-4-1-4-3
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pip check
```

La reinstalación actualiza las dependencias declaradas, también cuando el
paquete ya está instalado en modo editable. Esta rama utiliza
`pandas==3.1.0` y `yfinance==1.8.0`.

## Ejecutar las pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Las pruebas automatizadas simulan respuestas de las APIs, por lo que no
requieren Internet una vez instaladas las dependencias.

## Demostración sin conexión

```powershell
.\.venv\Scripts\python.exe ejemplos/demo_basica.py
```

El ejemplo utiliza precios sintéticos para mostrar las DataClasses y la cartera.

## Demostración completa de los apartados 4.1–4.3

```powershell
.\.venv\Scripts\python.exe ejemplos/demo_bloques_4_1_4_3.py
```

Requiere Internet. Descarga AAPL, MSFT y ^GSPC, consulta el PIB de España,
muestra las series mediante una interfaz común y construye una cartera
de dos acciones con pesos 0.6/0.4. El índice y el PIB se muestran por separado.
La [guía de los bloques 4.1–4.3](docs/guia_bloques_4_1_4_3.md) relaciona cada
requisito con su implementación y explica las decisiones para la presentación.

## Ejemplo con datos reales (requiere conexión)

```python
from miax_toolkit import Cartera, descargar_serie, descargar_series

apple = descargar_serie("AAPL", "2025-01-01", "2026-01-01")
indice = descargar_serie("^GSPC", "2025-01-01", "2026-01-01", tipo_activo="indice")
print(apple.media, apple.desviacion_tipica)

datos = descargar_series(["AAPL", "MSFT"], "2025-01-01", "2026-01-01")
cartera = Cartera("Ejemplo", list(datos.values()), {"AAPL": 0.6, "MSFT": 0.4})
print(cartera.obtener_pesos())
```

La fecha final es exclusiva. Los precios de cierre se descargan ajustados
mediante `auto_adjust=True`.

## Fuentes de datos (apartado 4.2)

- **Yahoo Finance:** acciones, índices y otros instrumentos cotizados. La
  función `descargar_serie()` devuelve un objeto `SeriePrecios`;
  `descargar_series()` procesa una lista de activos de forma secuencial.
- **Banco Mundial:** indicadores macroeconómicos anuales, como el PIB de España.
  La función `descargar_indicador()` devuelve `SerieIndicador`.

```python
from miax_toolkit import descargar_indicador
pib = descargar_indicador("ESP", "NY.GDP.MKTP.CD", 2020, 2024)
print(pib.valores)
```

Ambas fuentes ofrecen la misma interfaz de consulta: `valores` (una
`pandas.Series` numérica con fechas), `fuente` y `frecuencia`. Por ejemplo:

```python
for serie in [apple, pib]:
    print(serie.fuente, serie.frecuencia, serie.valores.head())
```

Los contenedores conservan sus metadatos específicos. En `SeriePrecios`,
`valores` da acceso a los mismos datos que `precios`, sin duplicarlos.

Un indicador macroeconómico no es una serie de precios y no se incluye
directamente en la cartera. La moneda puede indicarse al descargar un activo
o recuperarse, si está disponible, de Yahoo: primero se consultan los metadatos
históricos y después `fast_info["currency"]`. Si ambas consultas fallan o no
devuelven texto válido, queda `None` y se conservan los precios. La moneda
indicada expresamente tiene prioridad. No se convierten divisas.

## Modelado (apartado 4.3)

- `SeriePrecios`: DataClass con ticker, fuente, tipo de activo,
  moneda, frecuencia y precios con índice de fechas. Calcula automáticamente media y
  desviación típica muestral.
- `Cartera`: DataClass que agrupa activos y sus ponderaciones,
  valida la coincidencia de nombres y comprueba que los pesos sumen 1.
  Expone `obtener_precios()`, `obtener_pesos()` y
  `obtener_monedas()` para la futura integración.

## Organización y estado

- `src/miax_toolkit/`: paquete Python.
- `tests/`: pruebas automáticas.
- `ejemplos/`: demostración reproducible.
- `docs/fuentes_datos.md`: descripción de fuentes y limitaciones.
- `docs/guia_bloques_4_1_4_3.md`: requisitos, demostración y explicación de esta parte.
- `docs/revision_integracion.md`: comprobación de la interfaz con `monte-carlo`
  y puntos pendientes para una futura integración.

Los métodos de Monte Carlo, limpieza y reportes se desarrollan en otra rama
y todavía no están integrados.

## Verificación del 5 de noviembre de 2026

En una copia separada de esta rama y un entorno virtual nuevo con Python
3.12.8, pandas 3.1.0 y yfinance 1.8.0:

- Instalación editable correcta y `pip check` sin conflictos.
- 31 pruebas y 17 subcasos correctos con `python -m pytest -q -W error`, incluido
  el contrato multifuente y el rechazo de indicadores en la cartera.
- `ejemplos/demo_basica.py` y `ejemplos/demo_bloques_4_1_4_3.py` correctos.
- Lote real AAPL/MSFT/^GSPC, del 2025-01-01 al 2026-01-01: 250 observaciones
  por activo y moneda USD en los tres.
- Banco Mundial: PIB nominal de España, 2020–2024, con 5 observaciones.
- Sin avisos en esas consultas reales. No se han añadido filtros para ocultarlos.

Los avisos `Pandas4Warning` se reprodujeron con yfinance 1.7.0 y pandas 3.1.0.
yfinance 1.8.0 incorpora la [corrección de las llamadas `inplace`](https://github.com/ranaroussi/yfinance/pull/3020),
por lo que se actualiza únicamente esa dependencia directa y se mantiene pandas.
Estas comprobaciones cubren las funciones utilizadas en el taller, no todas
las funciones de yfinance ni todas las versiones admitidas de Python.
