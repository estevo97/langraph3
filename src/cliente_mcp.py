import sys
from pathlib import Path

from langchain_mcp_adapters.client import MultiServerMCPClient


# Ruta absoluta del servidor MCP
SERVIDOR = Path(__file__).resolve().parent / "server" / "server.py"


async def ejecutar_herramienta_mcp(nombre_herramienta: str, argumentos: dict):
    """Ejecuta una herramienta concreta del servidor MCP."""

    client = MultiServerMCPClient(
        {
            "gestor_documental": {
                "transport": "stdio",
                "command": sys.executable,
                "args": [str(SERVIDOR)],
            }
        }
    )

    # Descubrir las herramientas disponibles
    tools = await client.get_tools()

    # Buscar la herramienta solicitada
    herramienta = next(
        (tool for tool in tools if tool.name == nombre_herramienta),
        None
    )

    if herramienta is None:
        raise ValueError(
            f"No existe la herramienta MCP: {nombre_herramienta}"
        )

    # Ejecutar la herramienta
    return await herramienta.ainvoke(argumentos)