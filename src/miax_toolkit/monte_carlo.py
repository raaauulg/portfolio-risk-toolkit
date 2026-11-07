"""Motor de simulación de Monte Carlo con t de Student (apartado 4.4).

Modelo: cada día, el rendimiento logarítmico de cada activo es

    r = mu_d + sigma_d * Z

donde mu_d = mu / 252, sigma_d = sigma / raiz(252) y Z es una t de Student
estandarizada (media 0, varianza 1) con nu grados de libertad. Para la cartera,
los Z de los activos están correlacionados (t de Student multivariante).

El precio evoluciona como S(t+1) = S(t) * exp(r). Como mu es el retorno
logarítmico, no se resta sigma^2 / 2.

Limitaciones: volatilidad y correlación constantes, colas simétricas y
parámetros estimados con el pasado. Los resultados son escenarios posibles,
no predicciones.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .limpieza import validar_pesos

DIAS_POR_ANIO = 252


# 1. Estimar los parámetros con el histórico
def estimar_parametros(precios: pd.DataFrame):
    """Devuelve (mu, sigma, correlacion) anuales a partir de rendimientos logarítmicos."""
    rendimientos = np.log(precios).diff().dropna()
    mu = rendimientos.mean() * DIAS_POR_ANIO
    sigma = rendimientos.std() * np.sqrt(DIAS_POR_ANIO)
    correlacion = rendimientos.corr()
    return mu, sigma, correlacion


def _aplicar_supuesto(valor, historico: pd.Series, nombre: str) -> pd.Series:
    """None = histórico; un número = para todos; un diccionario = solo esos activos."""
    resultado = historico.copy()
    if isinstance(valor, dict):
        desconocidos = set(valor) - set(resultado.index)
        if desconocidos:
            raise ValueError(f"{nombre}: activos desconocidos {sorted(desconocidos)}.")
        for activo, dato in valor.items():
            resultado[activo] = dato
    elif valor is not None:
        resultado[:] = valor
    return resultado.astype(float)


# 2. Generar los shocks t de Student correlacionados
def _factor_cholesky(correlacion: pd.DataFrame) -> np.ndarray:
    """Cholesky de la correlación, con un error claro si no se puede calcular."""
    try:
        return np.linalg.cholesky(correlacion.to_numpy())
    except np.linalg.LinAlgError:
        raise ValueError(
            "La matriz de correlación no es definida positiva. Suele pasar si hay "
            "un activo duplicado o dos activos que se mueven exactamente igual."
        ) from None


def _shocks_t_student(generador, n_sims: int, factor: np.ndarray, nu: float) -> np.ndarray:
    """Shocks de un día, forma (n_sims, n_activos): media 0, varianza 1, correlacionados."""
    normales = generador.standard_normal((n_sims, factor.shape[0])) @ factor.T
    w = generador.chisquare(nu, size=(n_sims, 1))  # el mismo para todos los activos
    t = normales / np.sqrt(w / nu)                 # t de Student multivariante
    return t * np.sqrt((nu - 2) / nu)              # estandarizada: varianza 1


# 4. Resultado de la simulación
@dataclass
class SimulationResult:
    """Trayectorias simuladas, parámetros usados y resumen.

    trayectorias tiene forma (n_sims, horizonte + 1); la columna 0 es el valor inicial.
    """

    nombre: str
    trayectorias: np.ndarray
    parametros: dict = field(default_factory=dict)

    @property
    def valor_inicial(self) -> float:
        return float(self.trayectorias[0, 0])

    @property
    def valores_finales(self) -> np.ndarray:
        return self.trayectorias[:, -1]

    def percentiles(self, niveles=(5, 50, 95)) -> pd.DataFrame:
        """Percentiles del valor en cada día del horizonte."""
        datos = np.percentile(self.trayectorias, niveles, axis=0).T
        return pd.DataFrame(datos, columns=[f"P{n}" for n in niveles])

    def resumen(self) -> dict:
        """P5, P50, P95, valor esperado y probabilidad de pérdida al final del horizonte."""
        finales = self.valores_finales
        return {
            "valor_inicial": self.valor_inicial,
            "P5": float(np.percentile(finales, 5)),
            "P50": float(np.percentile(finales, 50)),
            "P95": float(np.percentile(finales, 95)),
            "valor_esperado": float(finales.mean()),
            "prob_perdida": float((finales < self.valor_inicial).mean()),
        }

    def interpretacion(self) -> str:
        """Explica el resumen en palabras."""
        r = self.resumen()
        dias = self.parametros.get("horizonte", self.trayectorias.shape[1] - 1)
        return (
            f"{self.nombre}, a {dias} días de mercado, partiendo de {r['valor_inicial']:.2f}:\n"
            f"- En el 5 % de los escenarios más desfavorables termina por debajo de {r['P5']:.2f} (P5).\n"
            f"- La mitad de los escenarios termina por encima de {r['P50']:.2f} (P50, mediana).\n"
            f"- Solo el 5 % de los escenarios supera {r['P95']:.2f} (P95).\n"
            f"- Valor medio de los escenarios: {r['valor_esperado']:.2f}.\n"
            f"- Probabilidad de terminar con pérdidas: {r['prob_perdida']:.1%}.\n"
            "Son escenarios posibles según los supuestos del modelo, no una predicción."
        )

    # 5. Visualización
    def plot(self, n_trayectorias: int = 50, mostrar: bool = True, ruta=None):
        """Dibuja las trayectorias y la distribución del valor final."""
        import matplotlib.pyplot as plt

        p = self.percentiles((5, 25, 50, 75, 95))
        dias = np.arange(len(p))
        azul = "#2a78d6"

        figura, (eje1, eje2) = plt.subplots(
            1, 2, figsize=(11, 5), sharey=True, width_ratios=[3, 1], layout="constrained"
        )
        eje1.plot(dias, self.trayectorias[:n_trayectorias].T, color=azul, alpha=0.12, linewidth=0.7)
        eje1.fill_between(dias, p["P5"], p["P95"], color=azul, alpha=0.15, label="Entre P5 y P95")
        eje1.fill_between(dias, p["P25"], p["P75"], color=azul, alpha=0.25, label="Entre P25 y P75")
        eje1.plot(dias, p["P50"], color=azul, linewidth=2, label="Mediana (P50)")
        eje1.axhline(self.valor_inicial, color="#52514e", linestyle="--", linewidth=1, label="Valor inicial")
        eje1.set_xlim(0, dias[-1])
        eje1.set_xlabel("Días de mercado")
        eje1.set_ylabel("Valor")
        eje1.set_title("Trayectorias simuladas", loc="left")
        eje1.legend(frameon=False, loc="upper left")

        # Histograma sin el 1 % de cada extremo, para que las colas no aplasten el gráfico
        bajo, alto = np.percentile(self.valores_finales, [1, 99])
        visibles = self.valores_finales[(self.valores_finales >= bajo) & (self.valores_finales <= alto)]
        eje2.hist(visibles, bins=40, orientation="horizontal", color=azul)
        r = self.resumen()
        eje2.axhline(r["P5"], color="#e34948", linewidth=1.5, label=f"P5: {r['P5']:.1f}")
        eje2.axhline(r["P50"], color="black", linewidth=1.5, label=f"P50: {r['P50']:.1f}")
        eje2.axhline(r["P95"], color="#1baf7a", linewidth=1.5, label=f"P95: {r['P95']:.1f}")
        eje2.set_xlabel("Nº de escenarios")
        eje2.set_title("Valor final", loc="left")
        eje2.legend(frameon=False, loc="upper right", fontsize=8)

        for eje in (eje1, eje2):
            eje.spines[["top", "right"]].set_visible(False)
            eje.grid(alpha=0.3)
        figura.suptitle(
            f"Monte Carlo t de Student (nu = {self.parametros.get('nu')}): {self.nombre}",
            x=0.01, ha="left", fontweight="bold",
        )
        if ruta is not None:
            figura.savefig(ruta, dpi=150)
        if mostrar:
            plt.show()
        return figura


# 3. Construir las trayectorias
def simular_cartera(
    precios: pd.DataFrame,
    pesos: dict,
    n_sims: int = 10_000,
    horizonte: int = 252,
    retorno=None,
    volatilidad=None,
    nu: float = 5,
    v0: float = 100.0,
    semilla: int | None = 42,
    nombre: str = "Cartera",
) -> SimulationResult:
    """Simula una cartera de comprar y mantener con shocks t de Student correlacionados.

    precios: tabla limpia y alineada (por ejemplo, el resultado de alinear_precios).
    retorno y volatilidad: anuales. None = histórico; un número = para todos los
    activos; un diccionario {activo: valor} = solo esos activos.
    nu: grados de libertad de la t de Student (mayor que 2; cuanto menor, más colas).
    """
    if n_sims < 1 or horizonte < 1:
        raise ValueError("n_sims y horizonte deben ser al menos 1.")
    if nu <= 2:
        raise ValueError("nu debe ser mayor que 2 para que la varianza exista.")
    if v0 <= 0:
        raise ValueError("v0 debe ser positivo.")

    w = validar_pesos(pesos, precios.columns).to_numpy()
    mu_hist, sigma_hist, correlacion = estimar_parametros(precios)
    mu = _aplicar_supuesto(retorno, mu_hist, "retorno")
    sigma = _aplicar_supuesto(volatilidad, sigma_hist, "volatilidad")
    if (sigma < 0).any():
        raise ValueError("La volatilidad no puede ser negativa.")
    factor = _factor_cholesky(correlacion.fillna(0.0))

    mu_d = mu.to_numpy() / DIAS_POR_ANIO
    sigma_d = sigma.to_numpy() / np.sqrt(DIAS_POR_ANIO)
    generador = np.random.default_rng(semilla)

    # Vectorizado: cada iteración avanza un día para TODAS las simulaciones a la vez.
    # (Generar todos los días de golpe ocuparía demasiada memoria con muchos activos.)
    valor_activos = np.tile(w * v0, (n_sims, 1))  # dinero en cada activo, forma (n_sims, n_activos)
    trayectorias = np.empty((n_sims, horizonte + 1))
    trayectorias[:, 0] = v0
    for dia in range(1, horizonte + 1):
        z = _shocks_t_student(generador, n_sims, factor, nu)
        valor_activos = valor_activos * np.exp(mu_d + sigma_d * z)
        trayectorias[:, dia] = valor_activos.sum(axis=1)

    parametros = {
        "n_sims": n_sims, "horizonte": horizonte, "nu": nu, "v0": v0, "semilla": semilla,
        "pesos": dict(zip(precios.columns, w)),
        "retorno": mu.to_dict(), "volatilidad": sigma.to_dict(),
    }
    return SimulationResult(nombre, trayectorias, parametros)


def simular_activo(precios: pd.Series, v0: float | None = None, **opciones) -> SimulationResult:
    """Simula un solo activo. Por defecto parte de su último precio."""
    nombre = str(precios.name or "Activo")
    tabla = precios.to_frame(nombre)
    v0 = float(precios.iloc[-1]) if v0 is None else v0
    return simular_cartera(tabla, {nombre: 1.0}, v0=v0, nombre=nombre, **opciones)