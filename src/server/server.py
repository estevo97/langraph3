
from pathlib import Path
import shutil
import os

from mcp.server.fastmcp import FastMCP


# --------------------------------------------------
# 1. CONFIGURACIÓN DEL SERVIDOR
# --------------------------------------------------

mcp = FastMCP("Gestor documental")

# Raíz del proyecto
BASE_DIR = Path(__file__).resolve().parents[2]

# Directorios de trabajo
DATOS_DIR = BASE_DIR / "datos"
RECEPCION = DATOS_DIR / "_recepcion"

# Directorio desde el que se copiarán los archivos.
# Se puede cambiar mediante una variable de entorno.
DIRECTORIO_ORIGEN = Path(
    os.getenv("DIRECTORIO_ORIGEN", str(Path.home() / "Downloads"))
).expanduser().resolve()

# Categorías permitidas
CATEGORIAS = {
    "deportes",
    "tecnologia",
    "ciencia",
    "economia",
    "politica",
    "educacion",
}

RECEPCION.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# 2. FUNCIONES AUXILIARES
# --------------------------------------------------

def validar_nombre(nombre: str) -> str:
    """Comprueba que se recibe un nombre de archivo simple."""

    if not nombre or nombre in {".", ".."}:
        raise ValueError("Nombre de archivo no válido.")

    if Path(nombre).name != nombre:
        raise ValueError("Solo se permite indicar el nombre del archivo.")

    return nombre


def obtener_categoria(tematica: str) -> Path:
    """Devuelve la ruta de una categoría permitida."""

    categoria = tematica.strip().lower()

    if categoria not in CATEGORIAS:
        raise ValueError(
            f"Categoría no permitida. Categorías disponibles: "
            f"{', '.join(sorted(CATEGORIAS))}"
        )

    return DATOS_DIR / categoria


# --------------------------------------------------
# 3. HERRAMIENTAS MCP
# --------------------------------------------------

@mcp.tool()
def copiar_archivo(nombre_archivo: str) -> str:
    """Copia un archivo del directorio de origen a recepción."""

    nombre_archivo = validar_nombre(nombre_archivo)

    origen = DIRECTORIO_ORIGEN / nombre_archivo
    destino = RECEPCION / nombre_archivo

    if not origen.is_file():
        return f"No se encuentra el archivo: {nombre_archivo}"

    if destino.exists():
        return f"El archivo ya existe en recepción: {nombre_archivo}"

    shutil.copy2(origen, destino)

    return f"Archivo copiado correctamente a recepción: {nombre_archivo}"


@mcp.tool()
def leer_archivo(nombre_archivo: str) -> str:
    """Lee el contenido de un archivo de texto situado en recepción."""

    nombre_archivo = validar_nombre(nombre_archivo)
    ruta = RECEPCION / nombre_archivo

    if not ruta.is_file():
        return f"No existe el archivo en recepción: {nombre_archivo}"

    try:
        return ruta.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return "No se ha podido interpretar el archivo como texto UTF-8."


@mcp.tool()
def guardar_texto(nombre_archivo: str, contenido: str) -> str:
    """Guarda un texto como archivo dentro de recepción."""

    nombre_archivo = validar_nombre(nombre_archivo)

    if not nombre_archivo.endswith(".txt"):
        nombre_archivo += ".txt"

    destino = RECEPCION / nombre_archivo

    if destino.exists():
        return f"Ya existe un archivo con ese nombre: {nombre_archivo}"

    destino.write_text(contenido, encoding="utf-8")

    return f"Texto guardado correctamente: {nombre_archivo}"


@mcp.tool()
def crear_carpeta(tematica: str) -> str:
    """Crea una carpeta para una categoría permitida."""

    carpeta = obtener_categoria(tematica)
    carpeta.mkdir(parents=True, exist_ok=True)

    return f"Carpeta disponible: {carpeta.name}"


@mcp.tool()
def mover_archivo(nombre_archivo: str, tematica: str) -> str:
    """Mueve un archivo de recepción a una categoría."""

    nombre_archivo = validar_nombre(nombre_archivo)

    origen = RECEPCION / nombre_archivo
    carpeta_destino = obtener_categoria(tematica)
    destino = carpeta_destino / nombre_archivo

    if not origen.is_file():
        return f"No existe el archivo en recepción: {nombre_archivo}"

    if destino.exists():
        return f"Ya existe un archivo con ese nombre en {tematica}."

    carpeta_destino.mkdir(parents=True, exist_ok=True)
    shutil.move(str(origen), str(destino))

    return f"Archivo movido correctamente a {tematica}: {nombre_archivo}"


@mcp.tool()
def listar_archivos(tematica: str) -> list[str]:
    """Lista los archivos existentes en una categoría."""

    carpeta = obtener_categoria(tematica)

    if not carpeta.is_dir():
        return []

    return sorted(
        archivo.name
        for archivo in carpeta.iterdir()
        if archivo.is_file()
    )

@mcp.tool()
def listar_recepcion() -> list[str]:
    """Lista los archivos pendientes de clasificar en recepción."""

    if not RECEPCION.is_dir():
        return []

    return sorted(
        archivo.name
        for archivo in RECEPCION.iterdir()
        if archivo.is_file()
    )
# --------------------------------------------------
# 4. ARRANQUE DEL SERVIDOR
# --------------------------------------------------

if __name__ == "__main__":
    mcp.run()
