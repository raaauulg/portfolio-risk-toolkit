# Informe de Cartera demo

## Resumen

| Métrica | Valor |
| --- | --- |
| Periodo | 03/01/2022 a 31/10/2025 (984 sesiones) |
| Rendimiento anualizado | 17,99 % |
| Volatilidad anualizada | 20,54 % |
| Ratio de Sharpe (tasa libre 2,00 %) | 0,81 |
| Ratio de Sortino | 1,18 |
| Caída máxima | -23,74 % |
| VaR diario histórico al 95 % | 2,04 % |
| CVaR diario histórico al 95 % | 2,69 % |
| Rebalanceo | diario |
| Beta frente a Índice | 0,75 |
| Tracking error frente a Índice | 9,44 % |

## Composición

| Activo | Peso | Aportación al riesgo |
| --- | --- | --- |
| TEC | 45,0 % | 62,8 % |
| BANCO | 25,0 % | 24,1 % |
| ENERGIA | 20,0 % | 13,4 % |
| BONOS | 10,0 % | -0,2 % |

Número efectivo de activos: 3,2 de 4.

## Métricas por activo

| Activo | Rendimiento anual | Volatilidad | Sharpe | Caída máxima |
| --- | --- | --- | --- | --- |
| TEC | 26,76 % | 31,20 % | 0,85 | -31,22 % |
| BANCO | 4,17 % | 25,80 % | 0,21 | -37,30 % |
| ENERGIA | 17,40 % | 24,36 % | 0,70 | -41,04 % |
| BONOS | 1,20 % | 6,16 % | -0,10 | -14,49 % |

## Correlaciones

Media entre pares: 0,17. Más alta: TEC/BANCO (0,53). Más baja: TEC/BONOS (-0,15).

## Simulación de Monte Carlo

| Métrica | Valor |
| --- | --- |
| Escenarios | 10.000 |
| Horizonte | 252 días de mercado |
| Valor inicial | 100,00 |
| Valor final mediano | 117,81 |
| Rango central del 90 % | 84,27 a 164,80 |
| Probabilidad de pérdida | 20,7 % |
| VaR al 95 % en el horizonte | 15,73 % |
| CVaR al 95 % en el horizonte | 22,64 % |

## Diagnóstico de los datos

- TEC: 1 precio(s) <= 0 tratados como dato ausente.
- TEC: 1 fecha(s) sin precio descartada(s).
- ENERGIA: 3 fecha(s) sin precio descartada(s).
- Alineación (interseccion): se descartan 16 de 1000 fechas por no tener precio de todos los activos.

## Advertencias de riesgo

- **ALTO:** Concentración: TEC pesa 45,0 %, por encima del límite de 40 %.
- **ALTO:** Riesgo concentrado: TEC aporta 62,8 % del riesgo con un peso de 45,0 %.
- **INFO:** Monte Carlo usa el retorno histórico como retorno futuro. Es el supuesto más débil: conviene probar otros valores.
- **INFO:** Las métricas son históricas o simuladas, no garantizan resultados futuros, y no incluyen costes, impuestos ni dividendos salvo que los precios ya estén ajustados.
