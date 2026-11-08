# Fuentes de datos — apartado 4.2

El toolkit utiliza dos servicios de datos:

- **Yahoo Finance**, mediante `yfinance`, para precios diarios de acciones,
  índices y otros instrumentos cotizados (por ejemplo, futuros sobre materias
  primas). La función `descargar_serie()` devuelve un objeto `SeriePrecios`.
  `descargar_series()` recibe una lista y devuelve un diccionario de estos objetos.
  Las descargas del lote se realizan de forma secuencial, no en paralelo.
- **Banco Mundial**, mediante su API pública sin clave, para indicadores
  macroeconómicos, como el PIB nominal. `descargar_indicador()` devuelve un
  objeto `SerieIndicador` con fechas anuales y valores numéricos.

Ambos extractores exponen `valores`, `fuente` y `frecuencia`. `valores` es una
`pandas.Series` de tipo `float64` con índice temporal ordenado y sin zona horaria.
La frecuencia es diaria en Yahoo y anual en Banco Mundial. En `SeriePrecios`,
`valores` es una propiedad que accede a `precios`; el código anterior sigue siendo
válido. Los contenedores conservan sus metadatos específicos. **Un indicador
macroeconómico no es una serie de precios**: no debe introducirse directamente
en una `Cartera` de activos cotizados.

## Ejemplos

```python
from miax_toolkit import descargar_serie, descargar_series, descargar_indicador, Cartera

apple = descargar_serie("AAPL", "2025-01-01", "2026-01-01", moneda="USD")
sp500 = descargar_serie("^GSPC", "2025-01-01", "2026-01-01", tipo_activo="indice")
oro = descargar_serie("GC=F", "2025-01-01", "2026-01-01", tipo_activo="materia_prima")
lote = descargar_series(["AAPL", "MSFT"], "2025-01-01", "2026-01-01")
cartera = Cartera("Ejemplo", list(lote.values()), {"AAPL": 0.6, "MSFT": 0.4})

pib = descargar_indicador("ESP", "NY.GDP.MKTP.CD", 2020, 2024)
print(pib.valores)
```

## Notas

- La fecha final de Yahoo Finance es exclusiva.
- Los cierres descargados se ajustan mediante `auto_adjust=True`.
- Las monedas pueden proporcionarse expresamente. Si no se indican, se intenta
  recuperarlas de los metadatos históricos de Yahoo Finance y, si falta un valor
  válido o falla la consulta, de `fast_info["currency"]`. Si tampoco se obtiene
  allí, la moneda queda como `None` y la descarga de precios sigue siendo válida.
  Se eliminan espacios y se normaliza a mayúsculas, como en la versión anterior.
  No se realiza conversión entre divisas; indicar una moneda solo fija metadatos.
- Una descarga que falle detiene el lote con un error; no se omiten activos
  silenciosamente.
- Las APIs externas requieren conexión, y pueden imponer límites o cambiar
  la disponibilidad de los datos.

## Metadatos y compatibilidad comprobados

En yfinance 1.7.0, `get_history_metadata()` devuelve `HistoryMetadata`, un
objeto de tipo `Mapping`, no un `dict`. La comprobación anterior lo descartaba
aunque tuviera `currency`. El extractor acepta ahora `Mapping` (incluidos los
diccionarios normales) y mantiene `fast_info` como segundo intento. Este último
también puede depender de los metadatos de Yahoo: no garantiza conocer la moneda.

Con pandas 3.1.0, las llamadas internas de yfinance 1.7.0 a operaciones como
`sort_index(inplace=True)` generan avisos de obsolescencia. `pip check` puede
pasar porque comprueba requisitos declarados, no la ausencia de avisos en
ejecución. Las descargas observadas seguían funcionando.

Se ha probado y fijado yfinance 1.8.0 con pandas 3.1.0: las consultas del README
terminaron sin avisos, sin aplicar parches locales a las bibliotecas ni añadir filtros
de advertencias. Referencias del proveedor:

- [Cambio de pandas 3.1 sobre `inplace`](https://pandas.pydata.org/pandas-docs/stable/whatsnew/v3.1.0.html#deprecated-inplace-keyword-for-various-methods).
- [Incidencia de yfinance 1.7.0](https://github.com/ranaroussi/yfinance/issues/3009).
- [Corrección incorporada](https://github.com/ranaroussi/yfinance/pull/3020) y
  [publicación de yfinance 1.8.0](https://github.com/ranaroussi/yfinance/releases/tag/1.8.0).
