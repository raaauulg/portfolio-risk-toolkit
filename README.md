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
git pull --ff-only
```

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

Un indicador macroeconómico no es una serie de precios y no se incluye
directamente en la cartera. La moneda puede indicarse al descargar un activo
o recuperarse, si está disponible, de Yahoo. No se convierten divisas.

## Modelado (apartado 4.3)

- `SeriePrecios`: DataClass con ticker, fuente, tipo de activo,
  moneda y precios con índice de fechas. Calcula automáticamente media y
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

Los métodos de Monte Carlo, limpieza y reportes se desarrollan en otra rama
y todavía no están integrados. Falta verificar la instalación en un entorno
limpio y probar las consultas reales a las APIs.
