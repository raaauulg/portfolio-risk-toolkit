"""Formato de números en estilo español: 1.234,56 · 12,3 % · 10.000 USD.

Solo da formato a valores que ya vienen calculados; no calcula nada.
"""

from datetime import date, datetime
import math

NO_DISPONIBLE = "n/d"


def _valido(x) -> bool:
    try:
        return x is not None and math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def numero(x, decimales: int = 2) -> str:
    """1234.5 -> '1.234,50'."""
    if not _valido(x):
        return NO_DISPONIBLE
    texto = f"{float(x):,.{decimales}f}"  # 1,234.50
    return texto.replace(",", " ").replace(".", ",").replace(" ", ".")


def porcentaje(x, decimales: int = 1, signo: bool = False) -> str:
    """0.1234 -> '12,3 %'. Con signo=True: '+12,3 %'."""
    if not _valido(x):
        return NO_DISPONIBLE
    texto = numero(float(x) * 100, decimales)
    if signo and float(x) > 0:
        texto = "+" + texto
    return f"{texto} %"


def puntos(x, decimales: int = 1) -> str:
    """Diferencia entre porcentajes en puntos porcentuales: 0.013 -> '+1,3 pp'."""
    if not _valido(x):
        return NO_DISPONIBLE
    texto = numero(float(x) * 100, decimales)
    return f"{'+' if float(x) > 0 else ''}{texto} pp"


def dinero(x, moneda: str | None, decimales: int = 0) -> str:
    """10000 -> '10.000 USD'."""
    if not _valido(x):
        return NO_DISPONIBLE
    return f"{numero(x, decimales)} {moneda or ''}".strip()


def fecha(valor) -> str:
    """Fecha en formato dd/mm/aaaa."""
    if isinstance(valor, (datetime, date)) or hasattr(valor, "strftime"):
        return valor.strftime("%d/%m/%Y")
    return str(valor)
