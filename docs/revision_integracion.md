# Revisión de la interfaz con Monte Carlo

Revisión del 5 de noviembre de 2026 desde `feat/bloques-4-1-4-3`, frente al
commit `208df754a79251135c4b61b262659bb5d96297f7` de `monte-carlo`.
No se ha fusionado esa rama ni se ha añadido herencia a `Cartera`.

## Contrato comprobado

| Método de Cartera | Salida actual | Compatibilidad con CarteraAnalisisMixin |
| --- | --- | --- |
| `obtener_precios()` | `{ticker: pandas.Series}` con fechas | Aceptada |
| `obtener_pesos()` | `{ticker: float}`, suma 1 | Aceptada; el análisis ordena los pesos según los precios |
| `obtener_monedas()` | Diccionario de monedas conocidas, o `None` | Aceptada; la información puede ser parcial |

Se hizo una comprobación temporal fuera del repositorio, utilizando los módulos
del commit indicado y una clase de prueba que combina `Cartera` con el mixin.
Con dos series sintéticas de 60 días y pesos 0.6/0.4 se verificaron
`preparar_datos()`, `report()` y `monte_carlo()` (10 iteraciones, 5 días,
semilla 42). Los pesos se pasaron en orden inverso para comprobar su alineación.
Esta prueba verifica la interfaz básica; no sustituye las pruebas completas de
la futura integración ni valida el modelo financiero.

## Puntos pendientes para integrar

- **Conectar las clases:** la `Cartera` de esta rama todavía no ofrece
  `monte_carlo()`, `report()` ni `plots_report()`. La herencia y las exportaciones
  del paquete se decidirán al integrar, conservando la API de los apartados 4.1–4.3.
- **Dependencias:** los gráficos de la otra rama necesitan `matplotlib`, pero
  su `pyproject.toml` aún no lo declara. Se confirmó `ModuleNotFoundError`
  al llamar a `plots_report()` en el entorno nuevo. No se añade aquí, porque
  los apartados 4.1–4.3 no lo utilizan. Al integrar habrá que conservar numpy,
  el extra `dev` y yfinance 1.8.0: la guía de esa rama aún muestra 1.7.0.
- **Historia mínima:** `SeriePrecios` admite dos precios válidos; el análisis
  exige al menos 30 observaciones diarias y 30 fechas comunes tras alinear.
  Se confirmó que una serie de 3 precios puede modelarse, pero el mixin la rechaza.
  No se cambia esa separación entre modelado y análisis.
- **Monedas desconocidas:** el informe avisa cuando recibe más de una moneda
  conocida. Se comprobó el aviso con USD/EUR y su ausencia con USD/`None`.
  La ausencia del aviso no demuestra una moneda común. No hay conversión de
  divisas y la recuperación de metadatos no elimina este límite.

Estos puntos se reservan para la integración conjunta. No se incorporan módulos,
dependencias gráficas ni reglas de análisis adicionales a esta rama.
