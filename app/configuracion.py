"""Configuración de un análisis y presets de un clic. Sin Streamlit: se prueba con pytest a secas."""

from dataclasses import dataclass, field

MAX_ACTIVOS = 8          # la paleta categórica tiene 8 colores; nunca se reciclan
MAX_ESCENARIOS = 20_000  # tope para que la app siga siendo fluida
NU_CASI_NORMAL = 200     # t de Student con 200 grados de libertad: prácticamente normal

# Benchmarks disponibles: ticker -> etiqueta. El S&P 500 se toma de FRED; los demás, de Yahoo.
BENCHMARKS = {
    "^GSPC": "S&P 500 (FRED)",
    "^STOXX50E": "Euro Stoxx 50 (Yahoo Finance)",
    "^IBEX": "IBEX 35 (Yahoo Finance)",
}


@dataclass(frozen=True)
class Configuracion:
    """Todo lo que define un análisis. Es inmutable y hashable: sirve de clave de caché."""

    modo: str                      # "instantanea" o "directo"
    activos: tuple[str, ...]
    pesos: tuple[float, ...]       # en tanto por uno, mismo orden que activos
    inicio: str                    # AAAA-MM-DD, inclusivo
    fin: str                       # AAAA-MM-DD, exclusivo (convención del toolkit)
    benchmark: str | None = None
    n_sims: int = 5_000
    horizonte: int = 252
    retorno: float | None = None   # anual; None = histórico
    volatilidad: float | None = None
    nu: float = 5.0
    semilla: int = 42
    v0: float = 10_000.0
    tasa_libre: float = 0.0
    nivel_var: float = 0.95
    nombre: str = "Mi cartera"

    @property
    def pesos_dict(self) -> dict[str, float]:
        return dict(zip(self.activos, self.pesos))


@dataclass(frozen=True)
class Preset:
    titulo: str
    descripcion: str
    config: Configuracion = field(repr=False)


_COMUN = dict(modo="instantanea", inicio="2021-01-01", fin="2026-01-01", n_sims=5_000,
              horizonte=252, nu=5.0, semilla=42, v0=10_000.0, tasa_libre=0.0, nivel_var=0.95)

PRESETS: dict[str, Preset] = {
    "demo": Preset(
        "Demo de la presentación",
        "Cinco empresas de distintos sectores de EE. UU. frente al S&P 500.",
        Configuracion(activos=("AAPL", "MSFT", "JPM", "JNJ", "XOM"),
                      pesos=(0.25, 0.20, 0.20, 0.20, 0.15), benchmark="^GSPC",
                      nombre="Cartera Demo (EE. UU.)", **_COMUN),
    ),
    "eeuu": Preset(
        "EE. UU. tecnológicas",
        "Cinco grandes tecnológicas a partes iguales: correlación y volatilidad altas.",
        Configuracion(activos=("AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"),
                      pesos=(0.2,) * 5, benchmark="^GSPC",
                      nombre="Tecnológicas EE. UU.", **_COMUN),
    ),
    "europa": Preset(
        "Europa (EUR)",
        "Seis valores de cuatro bolsas europeas frente al Euro Stoxx 50.",
        Configuracion(activos=("SAN.MC", "IBE.MC", "ITX.MC", "SAP.DE", "ASML.AS", "MC.PA"),
                      pesos=(1 / 6,) * 6, benchmark="^STOXX50E",
                      nombre="Cartera europea", **_COMUN),
    ),
}
