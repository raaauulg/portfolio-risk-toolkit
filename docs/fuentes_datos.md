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

Ambos extractores normalizan los datos numéricos a `pandas.Series` con
índice temporal y conservan su procedencia. Sin embargo, **un indicador
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
- Las monedas de los activos se introducen opcionalmente de forma explícita;
  no se convierten automáticamente entre divisas. Si no se conocen, no se
  debe asumir que todos los precios están en la misma moneda.
- Una descarga que falle detiene el lote con un error; no se omiten activos
  silenciosamente.
- Las APIs externas requieren conexión, y pueden imponer límites o cambiar
  la disponibilidad de los datos.
