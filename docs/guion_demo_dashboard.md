# Guion de la demo del dashboard (borrador)

Demo de 60-90 s dentro del bloque «Demo» de la presentación de 5 minutos
(2:30-4:00 en la hoja de ruta). El mensaje no es «hemos hecho una app»,
sino **«el toolkit está tan desacoplado que una capa nueva lo usa sin tocar
`src/`»**. El protagonista sigue siendo el toolkit.

## Antes de empezar

- Servidor arrancado y probado en el ordenador de la presentación, **sin
  Wi-Fi**: `.\.venv\Scripts\python.exe -m streamlit run app/dashboard.py`.
- Navegador abierto en `http://localhost:8501/?preset=demo` (la cartera Demo
  ya calculada), con zoom del navegador al 100-110 % para el proyector.
- Plan B: capturas en `docs/img/dashboard_*.png`, en el mismo orden que el guion.

## Guion (≈ 80 s)

| Tiempo | Qué se pulsa | Qué se dice |
| --- | --- | --- |
| 0-10 s | Nada (diapositiva anterior con las 6 líneas del README: `descargar_series` → `Cartera` → `monte_carlo()` → `report()`) | «Estas seis líneas son el toolkit. Lo que vais a ver ahora son exactamente esas llamadas, con una capa de presentación encima.» |
| 10-25 s | Página **Resumen** (ya abierta) | «Cartera de cinco sectores de EE. UU. frente al S&P 500 de FRED, con datos reales de 2021 a 2025. Todas las cifras salen de `reportes.metricas` y del informe: 19,5 % anual con un 16,2 % de volatilidad, caída máxima del 17,4 %. Las advertencias son las de `report()`.» |
| 25-40 s | **Cartera y riesgo** → gráfico «Peso frente a aportación al riesgo» | «Apple pesa un 25 % pero aporta un 35 % del riesgo; Johnson & Johnson pesa un 20 % y aporta solo un 8 %. Diversificar no es repartir pesos por igual.» |
| 40-65 s | **Monte Carlo** → bajar hasta el **comparador de colas** (está en «1 día») | «Monte Carlo con t de Student multivariante, `cartera.monte_carlo()`. La comparamos con nu = 200, prácticamente normal, misma semilla. En un día, las colas t son más extremas: el P0,1 baja de 9.720 a 9.604 USD. A un año la diferencia casi desaparece por el teorema central del límite; las colas gruesas importan para el riesgo a corto plazo.» |
| 65-80 s | Barra lateral: poner **AAPL al 50 %** y pulsar **Calcular** | «Y las validaciones también son del toolkit: los pesos ya no suman 1 y el aviso que aparece es el mensaje de su `ValueError`. Este dashboard no modifica ni una línea de `src/`.» |

Si sobra tiempo: página **Arquitectura** («el dashboard es un consumidor más de
la API pública; la lista de funciones que usa se genera leyendo sus imports»).

## Preguntas probables

- **¿Calcula algo el dashboard?** No: las métricas, el informe y las
  simulaciones son del toolkit. Solo deriva tres series para dibujarlas
  (drawdown, volatilidad móvil y rendimientos), en `app/transformaciones.py`,
  y los tests comprueban que coinciden con las figuras del núcleo.
- **¿Por qué tanta rentabilidad?** Los activos se eligieron a posteriori
  (sesgo de supervivencia) y el periodo es alcista; el informe lo advierte y
  la simulación calibra con ese histórico, así que su mediana es optimista.
- **¿Qué pasa sin Internet?** El modo por defecto es la instantánea de
  `data/sample/`; hay un test que bloquea la red y recorre todas las páginas.
- **¿Y si falla una descarga en directo?** Un fallo de red (`RuntimeError`)
  se muestra como error de conexión y sugiere el modo sin conexión; una
  consulta sin datos (`ValueError`) pide cambiar activos o fechas.
