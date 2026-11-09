# Instantánea sin conexión (data/sample)

Datos reales para usar el dashboard sin Internet. Los descargó el propio toolkit
(`descargar_series` y `descargar_sp500_fred`) con el script
`app/generar_instantanea.py` el **09/11/2026**. Desde la raíz del repositorio se
regeneran así (requiere Internet):

```powershell
.\.venv\Scripts\python.exe -m app.generar_instantanea
```

| Fichero | Contenido |
| --- | --- |
| `precios_eeuu.csv` | Cierres diarios de AAPL, MSFT, NVDA, AMZN, GOOGL, JPM, JNJ, XOM (Yahoo Finance) y S&P 500 `^GSPC` (FRED). USD. |
| `precios_europa.csv` | Cierres diarios de SAN.MC, IBE.MC, ITX.MC (Madrid), SAP.DE (Xetra), ASML.AS (Ámsterdam), MC.PA (París), Euro Stoxx 50 `^STOXX50E` e IBEX 35 `^IBEX` (Yahoo Finance). EUR. |
| `series.csv` | Metadatos de cada serie: fuente, tipo de activo, moneda, frecuencia, unidad, ajuste, periodo y fecha de descarga. |

- **Periodo:** del 2021-01-01 al 2026-01-01, con el fin exclusivo, como en los
  extractores. La primera sesión es el 04/01/2021 y la última, el 31/12/2025.
  Son cinco años completos: incluyen el mercado bajista de 2022 y la caída de
  abril de 2025.
- **Formato largo** (`fecha,ticker,cierre`): cada serie conserva su propio
  calendario bursátil. La alineación entre bolsas la hace el toolkit
  (`alinear_precios`) al analizar, no este fichero. En el universo europeo
  hay 1.281 fechas distintas entre las seis acciones y se conservan 1.274 con
  precio de todas ellas. Al cruzarlas con el Euro Stoxx 50 de Yahoo quedan
  1.258 fechas comunes. La ausencia de un dato no demuestra por sí sola que
  la bolsa estuviera cerrada; no se rellenan observaciones.
- **Ajuste:** las acciones son cierres ajustados por dividendos y splits
  (`auto_adjust=True`). Los índices son índices de precios, sin dividendos, así
  que la comparación con la cartera no es exactamente homogénea.
- **Precisión:** los precios se guardan con 6 decimales.
- **Al cargarlos**, `app/datos.py` crea objetos `SeriePrecios` cuya fuente
  indica que son una instantánea, por ejemplo «Yahoo Finance (instantánea
  09/11/2026)».

## Limitaciones

- **Sesgo de supervivencia:** los activos son grandes compañías de hoy, elegidas
  a posteriori. Una cartera formada con ellas en 2021 no habría sabido cuáles iban
  a seguir siendo grandes. Los resultados históricos tienden a ser optimistas.
- Los proveedores pueden revisar los datos: una descarga posterior puede no
  coincidir exactamente con esta.
- **Condiciones de uso:** los datos son de Yahoo Finance y FRED (el S&P 500 es
  propiedad de S&P Dow Jones Indices LLC). Se incluyen solo como muestra pequeña
  para un trabajo académico. No deben redistribuirse ni usarse con fines
  comerciales; se aplican las condiciones de cada proveedor.
