"""Activos de la instantánea sin conexión y su descripción legible.

Un universo agrupa activos de una sola moneda: el toolkit no convierte divisas
y rechaza carteras que las mezclan.
"""

from dataclasses import dataclass

INICIO = "2021-01-01"
FIN = "2026-01-01"  # exclusivo, como en los extractores del toolkit


@dataclass(frozen=True)
class Universo:
    clave: str
    titulo: str
    moneda: str
    acciones: tuple[str, ...]
    indices_yahoo: tuple[str, ...] = ()
    sp500_fred: bool = False


UNIVERSOS: dict[str, Universo] = {
    "eeuu": Universo(
        "eeuu", "EE. UU. (USD)", "USD",
        ("AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "JPM", "JNJ", "XOM"),
        sp500_fred=True,
    ),
    "europa": Universo(
        "europa", "Europa (EUR)", "EUR",
        ("SAN.MC", "IBE.MC", "ITX.MC", "SAP.DE", "ASML.AS", "MC.PA"),
        indices_yahoo=("^STOXX50E", "^IBEX"),
    ),
}

NOMBRES = {
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "NVIDIA", "AMZN": "Amazon",
    "GOOGL": "Alphabet", "JPM": "JPMorgan Chase", "JNJ": "Johnson & Johnson",
    "XOM": "Exxon Mobil", "SAN.MC": "Banco Santander", "IBE.MC": "Iberdrola",
    "ITX.MC": "Inditex", "SAP.DE": "SAP", "ASML.AS": "ASML", "MC.PA": "LVMH",
    "^GSPC": "S&P 500", "^STOXX50E": "Euro Stoxx 50", "^IBEX": "IBEX 35",
}
