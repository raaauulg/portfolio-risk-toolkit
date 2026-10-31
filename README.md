
# MIAX — Taller B1-T1

Proyecto académico en Python para la extracción de datos financieros, el análisis bursátil y la gestión de carteras.

## Objetivo

Construir una herramienta organizada en módulos que permita obtener datos de distintas fuentes, representarlos mediante un formato común y utilizarlos para analizar series de precios y carteras de inversión.

## Funcionalidades previstas para los apartados 4.2 y 4.3

- Descargar precios históricos de acciones e índices bursátiles.
- Incorporar al menos una fuente o un tipo de datos adicional.
- Obtener varias series a partir de una lista de activos.
- Estandarizar los datos descargados para que puedan utilizarse de forma conjunta.
- Representar las series de precios y las carteras mediante DataClasses.
- Gestionar los activos de una cartera y sus ponderaciones.
- Calcular automáticamente la media y la desviación típica al crear una serie de precios.

## Requisitos

- Python 3.12 o superior. La instalación se ha comprobado con Python 3.12.8.
- Git.
- Conexión a Internet para instalar las dependencias y consultar las fuentes de datos.
- Acceso al repositorio de GitHub.

Las dependencias principales están declaradas en `pyproject.toml`:

- pandas 3.1.0.
- yfinance 1.7.0.

## Instalación en Windows

Ejecutar los comandos desde una terminal que reconozca la instalación de Python mediante el comando `python`. Si se utiliza Anaconda, se puede abrir Anaconda Prompt.

### 1. Descargar el repositorio

```text
git clone https://github.com/JaviHdezOlba/miax-b1-t1.git
cd miax-b1-t1
```

### 2. Crear un entorno virtual

Comprobar primero la versión de Python:

```text
python --version
```

Debe ser Python 3.12 o superior. Después, crear el entorno:

```text
python -m venv .venv
```

### 3. Instalar el paquete y sus dependencias

Desde la carpeta principal del proyecto:

```text
.\.venv\Scripts\python.exe -m pip install -e .
```

La opción `-e` instala el proyecto en modo editable, lo que permite seguir modificando el código de `src` durante el desarrollo.

### 4. Comprobar la instalación

```text
.\.venv\Scripts\python.exe -c "import miax_toolkit, pandas, yfinance; print('Instalación correcta')"
```

Si los paquetes se cargan correctamente, aparecerá:

```text
Instalación correcta
```

## Estado del proyecto

En desarrollo. Se han preparado la estructura del paquete, el entorno de trabajo y la configuración de instalación.

Las funcionalidades de descarga de datos y modelado de series y carteras se implementarán progresivamente. Sus ejemplos de uso se incorporarán a este README.
