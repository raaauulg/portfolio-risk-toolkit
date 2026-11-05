# Validación de inputs (apartado 4.5)

**Pregunta:** ¿debe el programa admitir cualquier input que contenga una serie
temporal de precios, o conviene poner restricciones más estrictas?

**Decisión:** restricciones estrictas en la entrada. Un dato malo no siempre provoca
un error: muchas veces produce un número razonable pero falso, por ejemplo una
volatilidad mal anualizada. Es preferible parar con un mensaje claro.

No obstante, no se rechaza todo. Cada problema se trata según si tiene una
corrección segura:

| Problema | Tratamiento | Motivo |
| --- | --- | --- |
| No es Series o DataFrame, o no tiene fechas | Error | Sin fechas no hay serie temporal |
| Valores de texto o booleanos | Error | Convertirlos sería adivinar |
| Datos no diarios | Error | La anualización asume unas 252 sesiones al año |
| Menos de 30 observaciones | Error | Media y desviación poco fiables |
| Más del 20 % de nulos | Error | Rellenar tanto inventaría la serie |
| Fechas desordenadas o duplicadas | Se corrige y se registra | La corrección no es ambigua |
| Huecos cortos | Se rellenan hacia delante, 5 días como máximo | Es el último precio conocido |
| Precios <= 0 o infinitos | Se tratan como nulos y se registra | Rompen los logaritmos; suelen ser errores |
| Saltos diarios muy grandes | Solo aviso | Pueden ser reales o un split sin ajustar |
| Calendarios distintos | Intersección por defecto, unión opcional | Ver abajo |

**Nunca se rellena hacia atrás**, porque usaría en una fecha un precio que entonces
aún no se conocía (*look-ahead*).

**Intersección frente a unión.** La intersección no inventa precios, pero pierde
fechas. La unión conserva más fechas, pero los festivos rellenados tienen rendimiento
0 y reducen ligeramente la volatilidad y la correlación medidas.

**Pesos.** Deben coincidir con los activos y sumar 1. Se admiten pesos negativos
(posiciones cortas), pero el informe lo avisa.

**Limitación conocida: monedas.** Sumar activos en USD y EUR sin convertirlos no es
correcto. El toolkit no los convierte. Si la Cartera implementa `obtener_monedas()`,
el informe lo avisa.

Los límites son parámetros (`min_observaciones`, `max_pct_nulos`, `max_relleno`), así
que se pueden relajar a propósito sin tocar el código.
