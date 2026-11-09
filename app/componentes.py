"""Piezas de interfaz reutilizables: tarjetas KPI, avisos, estado vacío, errores y glosario."""

import logging

import streamlit as st

from app import textos
from app.analisis import Resultados
from app.datos import ErrorDeDatos
from app.formato import fecha

registro = logging.getLogger("miax_dashboard")

# Nivel del aviso del toolkit -> (función de Streamlit, icono, etiqueta).
_NIVELES = {
    "ALTO": (st.error, ":material/warning:", "Riesgo alto"),
    "MEDIO": (st.warning, ":material/error:", "Riesgo medio"),
    "INFO": (st.info, ":material/info:", "Información"),
}


def modo_tema() -> str:
    """'claro' u 'oscuro' según el tema del navegador; 'claro' si no se conoce (p. ej., en AppTest)."""
    return "oscuro" if st.context.theme.type == "dark" else "claro"


def resultados_o_estado_vacio() -> Resultados:
    """Devuelve los resultados aplicados o muestra instrucciones y detiene la página."""
    resultados = st.session_state.get("resultados")
    if resultados is None:
        st.info(textos.ESTADO_VACIO, icon=":material/arrow_back:")
        st.stop()
    return resultados


def cabecera(titulo: str, res: Resultados, *, calibracion: bool = False) -> None:
    """Título de página con el contexto del análisis en una línea."""
    st.title(titulo)
    fechas = (res.tabla if calibracion else res.tabla_analisis).index
    contexto = "Calibración histórica · " if calibracion else ""
    fuente = "Instantánea sin conexión" if res.config.modo == "instantanea" else "Datos en directo"
    st.caption(f"**{res.config.nombre}** · {contexto}{fecha(fechas[0])}–{fecha(fechas[-1])} · "
               f"{len(fechas):,} sesiones · {res.moneda} · {fuente}".replace(",", "."))


def tarjeta(columna, titulo: str, valor: str, ayuda: str, delta: str | None = None,
            delta_color: str = "off", flecha: bool = True) -> None:
    """Tarjeta KPI. Con flecha=False el delta es un dato complementario: nota gris, sin flecha."""
    columna.metric(titulo, valor, delta=delta, delta_color=delta_color if flecha else "off",
                   delta_arrow="auto" if flecha else "off", help=ayuda, border=True)


def advertencias(avisos: list[tuple[str, str]], informe: str) -> None:
    """Advertencias del informe con icono, etiqueta y color según su nivel."""
    if not avisos:  # si el formato del informe cambiara, se muestra tal cual
        seccion = informe.split("## Advertencias de riesgo", 1)
        st.markdown(seccion[1] if len(seccion) == 2 else "Sin advertencias.")
        return
    for nivel, texto in avisos:
        funcion, icono, etiqueta = _NIVELES.get(nivel, _NIVELES["INFO"])
        funcion(f"**{etiqueta}.** {texto}", icon=icono)


def mostrar_error(error: Exception, modo: str) -> None:
    """Muestra un error sin traceback, con un mensaje según su tipo."""
    # Convención del toolkit: RuntimeError = fallo de red o del proveedor (reintentar);
    # ValueError = la petición no es válida o no hay datos (cambiar ticker, fechas o pesos).
    if isinstance(error, RuntimeError):
        st.error(f"**No se pudieron descargar los datos (fallo de conexión o del proveedor).** {error}\n\n"
                 "Inténtalo de nuevo más tarde o cambia al modo **Instantánea**, que funciona sin conexión.",
                 icon=":material/wifi_off:")
    elif isinstance(error, ErrorDeDatos):
        texto = str(error)
        ayuda = "Cambia los activos o las fechas de la consulta."
        if modo == "directo" and "no devolvió" in texto:
            # yfinance a veces devuelve una tabla vacía en lugar de fallar sin red.
            ayuda = ("Puede ser un ticker inexistente, un rango sin sesiones o falta de conexión; "
                     "prueba el modo **Instantánea**, que funciona sin conexión.")
        st.warning(f"**No hay datos para esa consulta.** {texto}\n\n{ayuda}",
                   icon=":material/event_busy:")
    elif isinstance(error, ValueError):
        st.warning(f"**La configuración no es válida.** {error}", icon=":material/report:")
    else:
        registro.exception("Error inesperado en el dashboard")
        st.error("Ha ocurrido un error inesperado al calcular. El detalle está en la consola; "
                 "prueba con otro preset o recarga la página.", icon=":material/error:")


def glosario() -> None:
    """Glosario plegable al pie de cada página."""
    with st.expander("Glosario", icon=":material/menu_book:"):
        for termino, definicion in textos.GLOSARIO.items():
            st.markdown(f"**{termino}.** {definicion}")
