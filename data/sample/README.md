# Instantánea sin conexión (data/sample)

Datos reales para usar el dashboard sin Internet. Se descargaron el 09/11/2026
con `app/generar_instantanea.py`, que usa las funciones del propio toolkit
(`descargar_series` y `descargar_sp500_fred`). Para regenerarlos hace falta
conexión; desde la raíz del repositorio:

```powershell
.\.venv\Scripts\python.exe -m app.generar_instantanea
```

| Fichero | Contenido |
| --- | --- |
| `precios_eeuu.csv` | Cierres diarios de AAPL, MSFT, NVDA, AMZN, GOOGL, JPM, JNJ, XOM (Yahoo Finance) y S&P 500 `^GSPC` (FRED). USD. |
| `precios_europa.csv` | Cierres diarios de SAN.MC, IBE.MC, ITX.MC (Madrid), SAP.DE (Xetra), ASML.AS (Ámsterdam), MC.PA (París), Euro Stoxx 50 `^STOXX50E` e IBEX 35 `^IBEX` (Yahoo Finance). EUR. |
| `series.csv` | Metadatos de cada serie: fuente, tipo de activo, moneda, frecuencia, unidad, ajuste, periodo y fecha de descarga. |

El periodo va del 2021-01-01 al 2026-01-01, con la fecha final exclusiva, igual
que en los extractores: la primera sesión es el 04/01/2021 y la última, el
31/12/2025. Son cinco años completos, que incluyen el mercado bajista de 2022 y
la caída de abril de 2025.

Los CSV de precios están en formato largo (`fecha,ticker,cierre`) para que cada
serie conserve su propio calendario bursátil. La alineación entre bolsas no se
hace en estos ficheros, sino en el toolkit (`alinear_precios`) al analizar, y
no se rellenan observaciones: que falte un dato no demuestra por sí solo que la
bolsa estuviera cerrada. Como referencia, en el universo europeo hay 1.281
fechas distintas entre las seis acciones, de las que 1.274 tienen precio de
todas ellas; al cruzarlas además con el Euro Stoxx 50 quedan 1.258.

Las acciones son cierres ajustados por dividendos y splits (`auto_adjust=True`).
Los índices son índices de precios, sin dividendos, así que la comparación de
la cartera con ellos no es del todo homogénea. Los precios se guardan con 6
decimales.

Al cargar la instantánea, `app/datos.py` crea objetos `SeriePrecios` cuya
fuente indica el proveedor y la fecha de descarga, por ejemplo «Yahoo Finance
(instantánea 09/11/2026)».

## Limitaciones

Hay sesgo de supervivencia: los activos son grandes compañías de hoy, elegidas
a posteriori. Quien formara una cartera con ellas en 2021 no podía saber cuáles
seguirían siendo grandes, así que los resultados históricos tienden a ser
optimistas.

Los proveedores pueden revisar sus datos, por lo que una descarga posterior
puede no coincidir exactamente con esta.

Los datos proceden de Yahoo Finance y FRED, y el S&P 500 es propiedad de S&P
Dow Jones Indices LLC. Se incluyen solo como muestra pequeña para un trabajo
académico: no deben redistribuirse ni usarse con fines comerciales, y se
aplican las condiciones de uso de cada proveedor.
