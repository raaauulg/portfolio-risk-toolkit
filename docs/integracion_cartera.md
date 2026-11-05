# Cómo conectar Monte Carlo y los reportes con la Cartera

## 1. Añadir dependencias en `pyproject.toml`

```toml
dependencies = [
    "pandas==3.1.0",
    "yfinance==1.7.0",
    "numpy>=2.0",
    "matplotlib>=3.9",
]

[project.optional-dependencies]
dev = ["pytest>=8"]
```

## 2. Heredar el mixin en la Cartera

Solo hay que tocar el archivo de la Cartera. Los nombres de ejemplo (`series`,
`pesos`, `ticker`, `precios`) deben sustituirse por los reales:

```python
from miax_toolkit.cartera_analisis import CarteraAnalisisMixin

@dataclass
class Cartera(CarteraAnalisisMixin):
    nombre: str
    series: list[SeriePrecios]
    pesos: dict[str, float]

    def obtener_precios(self):
        return {s.ticker: s.precios for s in self.series}

    def obtener_pesos(self):
        return self.pesos
```

Requisitos de lo que devuelven:

- `obtener_precios()`: `{activo: pandas.Series}` con índice de fechas, o un DataFrame
  con una columna por activo.
- `obtener_pesos()`: `{activo: peso}` con los mismos nombres de activo; deben sumar 1.
- Opcional: `obtener_monedas()` devuelve `{activo: moneda}`.
- Opcional: un atributo `nombre`, que aparece en títulos e informes.

## 3. Uso

```python
sim = cartera.monte_carlo(n_iteraciones=10_000, horizonte_dias=252, semilla=42)
sim.plot()

sim_prudente = cartera.monte_carlo(retorno_anual=0.04, volatilidad_anual=0.25)
sim_activo = cartera.monte_carlo(activo="AAPL")

print(cartera.report(tasa_libre=0.03, benchmark=sp500, simulacion=sim))
cartera.plots_report(benchmark=sp500)
```

## 4. Comprobar

```text
python -m pip install -e ".[dev]"
python -m pytest
python ejemplos/demo_sintetica.py
python ejemplos/demo_yahoo.py
```
