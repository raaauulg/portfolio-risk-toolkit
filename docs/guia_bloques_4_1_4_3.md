# Guía de los apartados 4.1–4.3

Esta guía relaciona el enunciado con la implementación y sirve para preparar
la explicación de esta parte del taller. El trabajo está en
`feat/bloques-4-1-4-3`; no incluye la integración de los apartados 4.4–4.6.

## 1. Requisitos y dónde comprobarlos

| Apartado | Requisito | Implementación y evidencia |
| --- | --- | --- |
| 4.1 | README con instalación y ejemplos reproducibles | `README.md`, `ejemplos/demo_basica.py` y `ejemplos/demo_bloques_4_1_4_3.py` |
| 4.1 | Código organizado en `/src` | Paquete `src/miax_toolkit/` |
| 4.1 | Dependencias y configuración de instalación | `pyproject.toml`, `.gitignore`; instalación editable y `pip check` verificados |
| 4.2 | Históricos de acciones e índices | `descargar_serie()`; pruebas simuladas y consultas reales de AAPL, MSFT y ^GSPC |
| 4.2 | Salidas homogéneas e interoperables | Contrato común `valores`, `fuente`, `frecuencia`; test multifuente y demo con el mismo consumidor |
| 4.2 | Fuente o tipo adicional | `descargar_indicador()`: Banco Mundial, PIB de España |
| 4.2 | Descarga de N series | `descargar_series()` recibe una lista y descarga en lote secuencial |
| 4.3 | DataClass de precios con valores y metadatos | `SeriePrecios` en `modelos.py` |
| 4.3 | Cartera con activos y ponderaciones | `Cartera` en `cartera.py`, coincidencia de tickers y suma de pesos igual a 1 |
| 4.3 | Media y desviación típica automáticas | `SeriePrecios.__post_init__()`; ejemplo [90, 100, 110] → media 100 y desviación muestral 10 |

## 2. Cómo se estandarizan las dos fuentes

Los detalles de Yahoo y Banco Mundial quedan dentro de sus extractores.
Quien consume los datos utiliza los mismos atributos:

| Atributo | Contrato de las salidas de los extractores |
| --- | --- |
| `valores` | `pandas.Series` de tipo `float64`, con `DatetimeIndex` ordenado y sin zona horaria |
| `fuente` | Nombre del proveedor |
| `frecuencia` | `diaria` para los precios de Yahoo; `anual` para Banco Mundial |

Por ejemplo, la función `mostrar_serie()` de la demo completa funciona con
acciones, índices y PIB sin preguntar de qué proveedor procede cada objeto.

Las clases contenedoras siguen siendo distintas: `SeriePrecios` conserva los
metadatos de un activo y sus estadísticos; `SerieIndicador` conserva el país
y el código del indicador. La homogeneidad se aplica al formato de los datos
y a su interfaz de consulta. No se trata un indicador económico como un activo.

En `SeriePrecios`, `valores` es una propiedad que accede a la misma serie que
`precios`: no se guardan dos copias ni se cambia la API que utiliza `Cartera`.
La frecuencia diaria es el valor predeterminado; si se construye manualmente
una serie con otra frecuencia, debe indicarse al crearla.

Compartir formato no significa que las observaciones puedan mezclarse sin más:
el PIB es anual, los precios son diarios y sus unidades son distintas.
La demo muestra el PIB por separado y la cartera rechaza `SerieIndicador`.

## 3. Demostración paso a paso

Desde la raíz del repositorio, con el paquete instalado:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe ejemplos/demo_basica.py
.\.venv\Scripts\python.exe ejemplos/demo_bloques_4_1_4_3.py
```

Las pruebas y la demo básica no necesitan Internet. La demo completa sí:

1. Descarga AAPL, MSFT y ^GSPC para 2025 mediante una sola llamada por lote.
2. Consulta el PIB nominal de España de 2020 a 2024.
3. Muestra las cuatro series mediante la misma función de consulta.
4. Muestra los estadísticos calculados automáticamente al crear los precios.
5. Construye una cartera de AAPL/MSFT con pesos 0.6/0.4 y muestra sus monedas.
6. Muestra los valores del PIB por separado. ^GSPC se conserva como referencia.

La consulta real del 5 de noviembre de 2026 devolvió 250 precios por símbolo
y 5 observaciones del PIB. Son resultados observados, no una garantía sobre
la disponibilidad futura ni sobre revisiones de los proveedores.
Si una API falla, el error se comunica; no se sustituyen sus datos por simulados.

## 4. Qué debes poder explicar

- **Separación de responsabilidades:** los extractores conocen las APIs;
  `SeriePrecios` y `Cartera` trabajan con datos de pandas y no descargan nada.
  Por eso la demo básica puede funcionar sin conexión.
- **DataClasses:** agrupan datos relacionados y generan métodos como el
  constructor. `__post_init__()` ejecuta las validaciones y los cálculos
  inmediatamente después de construir el objeto.
- **Estadísticos:** se calculan sobre los precios válidos; `std(ddof=1)` es
  la desviación típica muestral. No es la volatilidad de las rentabilidades.
  Los cálculos se realizan al instanciar: para analizar precios modificados,
  crea una nueva `SeriePrecios`.
- **Cartera:** conserva activos y pesos, comprueba que corresponden a los
  mismos tickers y que los pesos suman 1. No suma directamente los niveles
  de precios ni calcula aquí simulaciones o rentabilidades de cartera.
- **Fechas:** el final de Yahoo es exclusivo; en Banco Mundial ambos años
  del intervalo son inclusivos. Las fechas anuales etiquetan el año del dato,
  no su fecha de publicación.
- **Monedas:** se recuperan cuando es posible y se pueden indicar manualmente.
  No hay conversión de divisas y `None` significa que la moneda no se conoce.
- **Pruebas:** las respuestas simuladas permiten comprobar casos normales y
  fallos sin depender de la red. Las consultas reales comprueban, por separado,
  que los proveedores funcionan en el momento de la ejecución.

## 5. Límite de este cierre

Los bloques 4.1–4.3 quedan implementados y comprobados en esta rama con el
contrato de salidas descrito. La instalación del proyecto completo deberá
volver a comprobarse cuando se integren los módulos del resto del grupo.
La revisión de su interfaz está en `revision_integracion.md`; Monte Carlo,
reportes, limpieza avanzada y el diagrama formal pertenecen a los bloques
4.4–4.6 y no se incorporan como parte de este cierre.
