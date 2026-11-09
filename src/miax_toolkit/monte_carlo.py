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
from numbers import Real

import numpy as np
import pandas as pd

from .limpieza import validar_pesos, validar_tabla

DIAS_POR_ANIO = 252


# Estimación de parámetros históricos
def estimar_parametros(precios: pd.DataFrame):
    """Devuelve retorno y volatilidad anualizados, y correlación de rendimientos logarítmicos."""
    validar_tabla(precios)
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
            if isinstance(dato, (bool, np.bool_)) or not isinstance(dato, Real) or not np.isfinite(dato):
                raise ValueError(f"{nombre} debe contener números reales finitos.")
            resultado[activo] = float(dato)
    elif valor is not None:
        if isinstance(valor, (bool, np.bool_)) or not isinstance(valor, Real):
            raise ValueError(f"{nombre} debe ser un número, un diccionario o None.")
        resultado[:] = valor
    try:
        resultado = resultado.astype(float)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{nombre} debe contener números finitos.") from error
    if not np.isfinite(resultado).all():
        raise ValueError(f"{nombre} debe contener números finitos.")
    return resultado


# Shocks t de Student correlacionados
def _factor_cholesky(correlacion: pd.DataFrame) -> np.ndarray:
    """Cholesky de la correlación, con un error claro si no se puede calcular."""
    try:
        return np.linalg.cholesky(correlacion.to_numpy())
    except np.linalg.LinAlgError:
        # Una correlación perfecta es válida: la matriz puede ser semidefinida.
        valores, vectores = np.linalg.eigh(correlacion.to_numpy())
        if valores.min() < -1e-10:
            raise ValueError("La matriz de correlación no es semidefinida positiva.") from None
        return vectores @ np.diag(np.sqrt(np.maximum(valores, 0)))


def _shocks_t_student(generador, n_sims: int, factor: np.ndarray, nu: float) -> np.ndarray:
    """Shocks de un día, forma (n_sims, n_activos): media 0, varianza 1, correlacionados."""
    normales = generador.standard_normal((n_sims, factor.shape[0])) @ factor.T
    w = generador.chisquare(nu, size=(n_sims, 1))  # el mismo para todos los activos
    t = normales / np.sqrt(w / nu)                 # t de Student multivariante
    return t * np.sqrt((nu - 2) / nu)              # estandarizada: varianza 1


# Resultado de la simulación
@dataclass
class SimulationResult:
    """Trayectorias simuladas, parámetros usados y resumen.

    trayectorias tiene forma (n_sims, horizonte + 1); la columna 0 es el valor inicial.
    """

    nombre: str
    trayectorias: np.ndarray
    parametros: dict = field(default_factory=dict)

    def __post_init__(self):
        originales = np.asarray(self.trayectorias)
        if np.iscomplexobj(originales) or originales.dtype.kind == "b":
            raise ValueError("Las trayectorias deben contener números reales.")
        self.trayectorias = np.array(originales, dtype=float, copy=True)
        self._validar()

    def _validar(self):
        datos = np.asarray(self.trayectorias)
        if (datos.ndim != 2 or datos.shape[0] < 1 or datos.shape[1] < 2
                or not np.isfinite(datos).all() or (datos <= 0).any()):
            raise ValueError("Las trayectorias deben ser positivas y finitas, con al menos un escenario y dos fechas.")
        if not np.allclose(datos[:, 0], datos[0, 0]):
            raise ValueError("Todos los escenarios deben partir del mismo valor inicial.")

    @property
    def valor_inicial(self) -> float:
        return float(self.trayectorias[0, 0])

    @property
    def valores_finales(self) -> np.ndarray:
        return self.trayectorias[:, -1]

    def percentiles(self, niveles=(5, 50, 95)) -> pd.DataFrame:
        """Percentiles del valor en cada día del horizonte."""
        self._validar()
        datos = np.percentile(self.trayectorias, niveles, axis=0).T
        return pd.DataFrame(datos, columns=[f"P{n}" for n in niveles])

    def resumen(self) -> dict:
        """Percentiles, media muestral y probabilidad de pérdida; no estima una esperanza finita."""
        self._validar()
        finales = self.valores_finales
        return {
            "valor_inicial": self.valor_inicial,
            "P5": float(np.percentile(finales, 5)),
            "P50": float(np.percentile(finales, 50)),
            "P95": float(np.percentile(finales, 95)),
            "media_escenarios": float((finales / len(finales)).sum()),
            "prob_perdida": float((finales < self.valor_inicial).mean()),
        }

    def interpretacion(self) -> str:
        """Explica el resumen en palabras."""
        r = self.resumen()
        dias = self.trayectorias.shape[1] - 1
        return (
            f"{self.nombre}, a {dias} días de mercado, partiendo de {r['valor_inicial']:.2f}:\n"
            f"- Percentil 5 del valor final (P5): {r['P5']:.2f}.\n"
            f"- Mediana del valor final (P50): {r['P50']:.2f}.\n"
            f"- Percentil 95 del valor final (P95): {r['P95']:.2f}.\n"
            f"- Media muestral de los escenarios: {r['media_escenarios']:.2f} (inestable con colas t).\n"
            f"- Probabilidad de terminar con pérdidas: {r['prob_perdida']:.1%}.\n"
            "Son escenarios posibles según los supuestos del modelo, no una predicción."
        )

    # Visualización
    def plot(self, n_trayectorias: int = 50, mostrar: bool = True, ruta=None):
        """Dibuja las trayectorias y la distribución del valor final."""
        import matplotlib.pyplot as plt

        if (isinstance(n_trayectorias, (bool, np.bool_))
                or not isinstance(n_trayectorias, (int, np.integer)) or n_trayectorias < 1):
            raise ValueError("n_trayectorias debe ser un entero de al menos 1.")
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
        # Con dos escenarios distintos, ambos quedan fuera de P1–P99.
        recortado = len(visibles) > 0 and len(visibles) < len(self.valores_finales)
        if not len(visibles):
            visibles = self.valores_finales
        eje2.hist(visibles, bins=40, orientation="horizontal", color=azul)
        r = self.resumen()
        eje2.axhline(r["P5"], color="#e34948", linewidth=1.5, label=f"P5: {r['P5']:.1f}")
        eje2.axhline(r["P50"], color="black", linewidth=1.5, label=f"P50: {r['P50']:.1f}")
        eje2.axhline(r["P95"], color="#1baf7a", linewidth=1.5, label=f"P95: {r['P95']:.1f}")
        eje2.set_xlabel("Nº de escenarios")
        eje2.set_title("Valor final (P1–P99)" if recortado else "Valor final (todos)", loc="left")
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


# Construcción de trayectorias
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
    min_observaciones: int = 30,
) -> SimulationResult:
    """Simula una cartera de comprar y mantener con shocks t de Student correlacionados.

    precios: tabla limpia y alineada (por ejemplo, el resultado de alinear_precios).
    retorno y volatilidad: anuales. None = histórico; un número = para todos los
    activos; un diccionario {activo: valor} = solo esos activos.
    nu: grados de libertad de la t de Student (mayor que 2; cuanto menor, más colas).
    """
    if any(isinstance(x, bool) or not isinstance(x, (int, np.integer)) or x < 1 for x in (n_sims, horizonte)):
        raise ValueError("n_sims y horizonte deben ser enteros de al menos 1.")
    if isinstance(nu, (bool, np.bool_)) or not isinstance(nu, Real) or not np.isfinite(nu) or nu <= 2:
        raise ValueError("nu debe ser mayor que 2 para que la varianza exista.")
    if isinstance(v0, (bool, np.bool_)) or not isinstance(v0, Real) or not np.isfinite(v0) or v0 <= 0:
        raise ValueError("v0 debe ser positivo y finito.")
    if semilla is not None and (isinstance(semilla, bool) or not isinstance(semilla, (int, np.integer)) or semilla < 0):
        raise ValueError("semilla debe ser un entero no negativo o None.")
    validar_tabla(precios, min_observaciones)

    w = validar_pesos(pesos, precios.columns).to_numpy()
    mu_hist, sigma_hist, correlacion = estimar_parametros(precios)
    mu = _aplicar_supuesto(retorno, mu_hist, "retorno")
    sigma = _aplicar_supuesto(volatilidad, sigma_hist, "volatilidad")
    if (sigma < 0).any():
        raise ValueError("La volatilidad no puede ser negativa.")
    # Un activo constante tiene volatilidad cero. Si se impone una volatilidad,
    # se usa correlación cero: no implica independencia con una t multivariante.
    correlacion = correlacion.fillna(0.0)
    for activo in correlacion.columns:
        correlacion.loc[activo, activo] = 1.0
    factor = _factor_cholesky(correlacion)

    mu_d = mu.to_numpy() / DIAS_POR_ANIO
    sigma_d = sigma.to_numpy() / np.sqrt(DIAS_POR_ANIO)
    generador = np.random.default_rng(semilla)

    # Vectorizado: cada iteración avanza un día para TODAS las simulaciones a la vez.
    # (Generar todos los días de golpe ocuparía demasiada memoria con muchos activos.)
    valor_activos = np.tile(w * v0, (n_sims, 1))  # dinero en cada activo, forma (n_sims, n_activos)
    trayectorias = np.empty((n_sims, horizonte + 1))
    trayectorias[:, 0] = v0
    try:
        with np.errstate(over="raise", invalid="raise", under="raise"):
            for dia in range(1, horizonte + 1):
                z = _shocks_t_student(generador, n_sims, factor, nu)
                valor_activos = valor_activos * np.exp(mu_d + sigma_d * z)
                trayectorias[:, dia] = valor_activos.sum(axis=1)
    except FloatingPointError as error:
        raise ValueError("La simulación excede el rango numérico; revisa retorno, volatilidad, horizonte y nu.") from error

    parametros = {
        "n_sims": n_sims, "horizonte": horizonte, "nu": nu, "v0": v0, "semilla": semilla,
        "pesos": dict(zip(precios.columns, w)),
        "retorno": mu.to_dict(), "volatilidad": sigma.to_dict(),
        "fecha_inicio": precios.index[0].date().isoformat(),
        "fecha_fin": precios.index[-1].date().isoformat(),
        "observaciones": len(precios),
    }
    return SimulationResult(nombre, trayectorias, parametros)


def simular_activo(precios: pd.Series, v0: float | None = None, **opciones) -> SimulationResult:
    """Simula un solo activo. Por defecto parte de su último precio."""
    if not isinstance(precios, pd.Series) or precios.empty:
        raise ValueError("Se necesita una serie de precios no vacía.")
    nombre = str(precios.name or "Activo")
    tabla = precios.to_frame(nombre)
    validar_tabla(tabla, opciones.get("min_observaciones", 30))
    v0 = float(precios.iloc[-1]) if v0 is None else v0
    return simular_cartera(tabla, {nombre: 1.0}, v0=v0, nombre=nombre, **opciones)
