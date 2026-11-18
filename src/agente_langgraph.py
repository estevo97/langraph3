# -*- coding: utf-8 -*-
from dotenv import load_dotenv
import os 
import os
from pathlib import Path
from typing import TypedDict, Annotated
from dotenv import load_dotenv

from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from src.llm import crear_llm
import asyncio
from src.cliente_mcp import ejecutar_herramienta_mcp
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

load_dotenv()
GEMINI_API_KEY=os.getenv("GEMINI_API_KEY")


@tool
def calculator(expression: str) -> str:
    """Útil para realizar cálculos matemáticos exactos. Ingresa la expresión matemática."""
    try:
        result = eval(expression, {"__builtins__": None})
        return str(result)
    except Exception as e:
        return f"Error en el cálculo: {e}"


# EL ESTADO Y EL MODELO

print("Selecciona el proveedor del modelo:")
print("1. Gemini")
print("2. Ollama")

opcion = input("Opción: ").strip()

if opcion == "1":
    proveedor = "gemini"
elif opcion == "2":
    proveedor = "ollama"
else:
    raise ValueError("Opción no válida")

llm = crear_llm(proveedor=proveedor)

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    next_agent: str 

#llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
llm = crear_llm(
    proveedor=proveedor
)


# LOS NODOS

def nodo_enrutador(state: AgentState):
    """Analiza la petición y decide a qué agente enviarla."""
    mensaje_usuario = state["messages"][-1].content
    
    prompt = (
        "Eres un sistema de enrutamiento. Tu única tarea es clasificar "
        "el mensaje del usuario.\n"
        "Si el usuario pide cálculos, números o resolver problemas lógicos, "
        "responde: matematico\n"
        "Si el usuario pide escribir, rimas, literatura o algo creativo, "
        "responde: poeta\n"
        "Si el usuario pide consultar o listar documentos de una categoría, "
        "responde: listar_documentos\n"
        "Si el usuario pide clasificar u organizar los documentos pendientes "
        "de recepción, responde: clasificar_documentos\n"
        "Si el usuario pide copiar un archivo a recepción, "
        "responde: copiar_archivos\n"
        "Si el usuario pide leer un archivo de recepción, "
        "responde: leer_archivo\n"
        "Si el usuario pide guardar un texto en recepción, "
        "responde: guardar_texto\n"
        "Si el usuario hace preguntas científicas, responde: cientifico\n"
        "Responde ÚNICAMENTE con una de estas ocho opciones: "
        "matematico, poeta, listar_documentos, "
        "clasificar_documentos, copiar_archivos, leer_archivo, "
        "guardar_texto o cientifico.\n"
        "En minúsculas y sin puntuación.\n"
        f"Mensaje: {mensaje_usuario}"
    )
    
    respuesta = llm.invoke(prompt)
    
    contenido = respuesta.content
    
    # Verificamos si Gemini nos ha devuelto una lista de bloques
    if isinstance(contenido, list):
        # Extraemos el texto del primer bloque
        if len(contenido) > 0 and isinstance(contenido[0], dict) and "text" in contenido[0]:
            texto = contenido[0]["text"]
        else:
            texto = str(contenido[0])
    else:
        # Si es un texto normal
        texto = str(contenido)
        
    destino = texto.strip().lower()

    
    # por seguridad, por lo que pueda devolver el llm
    if "matematico" in destino:
        destino = "matematico"
    elif "listar_documentos" in destino:
        destino = "listar_documentos"
    elif "clasificar_documentos" in destino:
        destino = "clasificar_documentos"
    elif "copiar_archivos" in destino:
        destino = "copiar_archivos"
    elif "leer_archivo" in destino:
        destino = "leer_archivo"
    elif "guardar_texto" in destino:
        destino = "guardar_texto"
    elif "poeta" in destino:
        destino = "poeta"
    elif "cientifico" in destino:
        destino = "cientifico"
    else:
        destino = "poeta"
        
    print(f" [Enrutador] Desviando consulta hacia: {destino.upper()}")
    
    return {"next_agent": destino}

def nodo_matematico(state: AgentState):
    """Es experto en números, tiene calculadora integrada)"""
    print("[Agente Matemático] calculando...")
    
    #Creamos un sub-agente exclusivo para este nodo, dándole la herramienta
    math_agent = create_react_agent(llm, tools=[calculator])
    
    #Definimos su personalidad (inyectada de forma segura para tu versión de LangGraph)
    prompt_sistema = SystemMessage(
        content="Eres un matemático brillante pero muy arrogante y gruñón. "
                "USA OBLIGATORIAMENTE la herramienta 'calculator' para resolver la operación. "
                "Quéjate de que te hagan preguntas tan aburridas y fáciles."
    )
    
    #Preparamos los mensajes: Personalidad + Historial del usuario
    mensajes_para_agente = [prompt_sistema] + state["messages"]
    
    #Ejecutamos el sub-agente
    respuesta_sub_agente = math_agent.invoke({"messages": mensajes_para_agente})
    
    #Extraemos solo el mensaje final que nos dio el sub-agente para devolverlo al grafo principal
    respuesta_final = respuesta_sub_agente["messages"][-1]
    
    return {"messages": [respuesta_final]}

def nodo_poeta(state: AgentState):
    """Un experto en letras (Llamada simple, sin herramientas)."""
    print("[Agente Poeta] Recurriendo a las musas...")
    
    prompt_sistema = SystemMessage(
        content="Eres un poeta clásico y dramático del siglo XIX. "
                "Responde usando una poesía que rime. Usa palabras grandilocuentes."
    )
    
    # Como el poeta no necesita herramientas, hacemos un invoke() directo al LLM
    respuesta = llm.invoke([prompt_sistema] + state["messages"])
    
    return {"messages": [respuesta]}


def nodo_cientifico(state: AgentState):
    """Un experto científico que responde con rigor y evidencia."""
    print("[Agente Científico] Analizando los hechos...")

    prompt_sistema = SystemMessage(
        content=(
            "Eres un científico experto en física, química, biología "
            "y otras disciplinas científicas. "
            "Responde con rigor, precisión y basándote en evidencias "
            "y conocimientos científicos contrastados. "
            "Explica los conceptos complejos de forma clara y didáctica. "
            "Distingue entre hechos demostrados, hipótesis y teorías. "
            "Si no conoces la respuesta con suficiente certeza, "
            "reconócelo en lugar de inventar información. "
            "Utiliza un tono profesional, objetivo y analítico.\n"
        )
    )

    respuesta = llm.invoke([prompt_sistema] + state["messages"])

    return {"messages": [respuesta]}


async def nodo_listar_documentos(state: AgentState):
    """Lista los documentos de una categoría."""

    mensaje_usuario = state["messages"][-1].content.lower()

    categorias = {
        "deportes",
        "tecnologia",
        "ciencia",
        "economia",
        "politica",
        "educacion",
    }

    # Identificar la categoría indicada por el usuario
    tematica = next(
        (categoria for categoria in categorias if categoria in mensaje_usuario),
        None
    )

    if tematica is None:
        respuesta = (
            "Indica una categoría válida: deportes, tecnologia, "
            "ciencia, economia, politica o educacion."
        )
    else:
        resultado = await ejecutar_herramienta_mcp(
            "listar_archivos",
            {"tematica": tematica}
        )

        if not resultado:
            respuesta = f"No hay documentos en la categoría {tematica}."
        else:
            archivos = "\n".join(f"- {archivo}" for archivo in resultado)
            respuesta = f"Documentos de {tematica}:\n{archivos}"

    return {"messages": [AIMessage(content=respuesta)]}

async def nodo_clasificar_documentos(state: AgentState):
    """Lee los documentos de recepción, los clasifica y los mueve."""

    print("[Clasificador] Buscando documentos pendientes...")

    # 1. Obtener los archivos de recepción
    resultado = await ejecutar_herramienta_mcp(
        "listar_recepcion",
        {}
    )

    archivos = [
        bloque["text"]
        for bloque in resultado
        if bloque.get("type") == "text"
    ]

    if not archivos:
        return {
            "messages": [
                AIMessage(content="No hay documentos pendientes de clasificar.")
            ]
        }

    resultados = []

    # 2. Procesar cada documento
    for nombre_archivo in archivos:

        print(f"[Clasificador] Analizando: {nombre_archivo}")

        # Leer el documento
        contenido_resultado = await ejecutar_herramienta_mcp(
            "leer_archivo",
            {"nombre_archivo": nombre_archivo}
        )

        contenido = contenido_resultado[0]["text"]

        # 3. Preguntar a Gemini por la categoría
        prompt = f"""
        Clasifica el siguiente documento en UNA de estas categorías:

        deportes
        tecnologia
        ciencia
        economia
        politica
        educacion

        Devuelve únicamente el nombre de la categoría,
        en minúsculas y sin explicaciones.

        Nombre del archivo: {nombre_archivo}

        Contenido:
        {contenido}
        """

        respuesta = llm.invoke(prompt)
        contenido_respuesta = respuesta.content

        if isinstance(contenido_respuesta, list):
            tematica = contenido_respuesta[0]["text"].strip().lower()
        else:
            tematica = str(contenido_respuesta).strip().lower()

        # 4. Validar la categoría
        categorias_validas = {
            "deportes",
            "tecnologia",
            "ciencia",
            "economia",
            "politica",
            "educacion",
        }

        if tematica not in categorias_validas:
            resultados.append(
                f"No se pudo clasificar {nombre_archivo}: categoría no válida."
            )
            continue

        # 5. Mover el archivo a su categoría
        movimiento = await ejecutar_herramienta_mcp(
            "mover_archivo",
            {
                "nombre_archivo": nombre_archivo,
                "tematica": tematica
            }
        )

        # Extraer el texto de la respuesta MCP
        if isinstance(movimiento, list):
            texto_movimiento = "\n".join(
                bloque["text"]
                for bloque in movimiento
                if bloque.get("type") == "text"
            )
        else:
            texto_movimiento = str(movimiento)

        resultados.append(texto_movimiento)

    respuesta_final = "\n".join(resultados)

    return {
        "messages": [
            AIMessage(content=respuesta_final)
        ]
    }


async def nodo_copiar_archivos(state: AgentState):
    """Copia a recepción el archivo indicado por el usuario."""

    mensaje_usuario = state["messages"][-1].content
    prompt = (
        "Extrae del mensaje del usuario el nombre exacto del archivo que "
        "quiere copiar a recepción. Devuelve solo el nombre base del archivo, "
        "sin ruta ni explicaciones. No inventes nombres. Si no se indica "
        "claramente un nombre de archivo, devuelve exactamente "
        "NO_ESPECIFICADO.\n"
        f"Mensaje: {mensaje_usuario}"
    )
    contenido_nombre = llm.invoke(prompt).content

    if isinstance(contenido_nombre, list):
        nombre_archivo = next(
            (
                bloque["text"]
                for bloque in contenido_nombre
                if isinstance(bloque, dict)
                and isinstance(bloque.get("text"), str)
            ),
            "",
        )
    else:
        nombre_archivo = str(contenido_nombre)

    nombre_archivo = nombre_archivo.strip().strip("\"'`")
    if not nombre_archivo or nombre_archivo.upper() == "NO_ESPECIFICADO":
        return {
            "messages": [
                AIMessage(
                    content="Indica el nombre exacto del archivo que quieres copiar."
                )
            ]
        }

    if (
        nombre_archivo in {".", ".."}
        or Path(nombre_archivo).name != nombre_archivo
    ):
        return {
            "messages": [
                AIMessage(
                    content="Indica solo el nombre del archivo, sin incluir su ruta."
                )
            ]
        }

    resultado = await ejecutar_herramienta_mcp(
        "copiar_archivo",
        {"nombre_archivo": nombre_archivo}
    )

    if isinstance(resultado, list):
        respuesta = "\n".join(
            bloque["text"]
            for bloque in resultado
            if isinstance(bloque, dict)
            and bloque.get("type") == "text"
            and isinstance(bloque.get("text"), str)
        )
    else:
        respuesta = str(resultado)

    return {"messages": [AIMessage(content=respuesta or str(resultado))]}


async def nodo_leer_archivo(state: AgentState):
    """Lee y devuelve al usuario el contenido de un archivo en recepción."""

    mensaje_usuario = state["messages"][-1].content
    prompt = (
        "Extrae del mensaje del usuario el nombre exacto del archivo que "
        "quiere leer en recepción. Devuelve solo el nombre base del archivo, "
        "sin ruta ni explicaciones. No inventes nombres. Si no se indica "
        "claramente un nombre de archivo, devuelve exactamente "
        "NO_ESPECIFICADO.\n"
        f"Mensaje: {mensaje_usuario}"
    )
    contenido_nombre = llm.invoke(prompt).content

    if isinstance(contenido_nombre, list):
        nombre_archivo = next(
            (
                bloque["text"]
                for bloque in contenido_nombre
                if isinstance(bloque, dict)
                and isinstance(bloque.get("text"), str)
            ),
            "",
        )
    else:
        nombre_archivo = str(contenido_nombre)

    nombre_archivo = nombre_archivo.strip().strip("\"'`")
    if not nombre_archivo or nombre_archivo.upper() == "NO_ESPECIFICADO":
        return {
            "messages": [
                AIMessage(content="Indica el nombre exacto del archivo que quieres leer.")
            ]
        }

    if (
        nombre_archivo in {".", ".."}
        or Path(nombre_archivo).name != nombre_archivo
    ):
        return {
            "messages": [
                AIMessage(
                    content="Indica solo el nombre del archivo, sin incluir su ruta."
                )
            ]
        }

    resultado = await ejecutar_herramienta_mcp(
        "leer_archivo",
        {"nombre_archivo": nombre_archivo}
    )

    if isinstance(resultado, list):
        contenido = "\n".join(
            bloque["text"]
            for bloque in resultado
            if isinstance(bloque, dict)
            and bloque.get("type") == "text"
            and isinstance(bloque.get("text"), str)
        )
    else:
        contenido = str(resultado)

    return {
        "messages": [
            AIMessage(content=f"Contenido de {nombre_archivo}:\n{contenido}")
        ]
    }


async def nodo_guardar_texto(state: AgentState):
    """Guarda en recepción el texto incluido en el mensaje del usuario."""

    mensaje_usuario = state["messages"][-1].content
    prefijo, separador, contenido = mensaje_usuario.partition(":")

    if not separador:
        return {
            "messages": [
                AIMessage(
                    content=(
                        "Indica el nombre y el texto con este formato: "
                        "Guardar texto archivo.txt: contenido"
                    )
                )
            ]
        }

    partes_prefijo = prefijo.strip().split()
    if len(partes_prefijo) < 3:
        return {
            "messages": [
                AIMessage(
                    content=(
                        "Indica el nombre del archivo antes de los dos puntos. "
                        "Ejemplo: Guardar texto archivo.txt: contenido"
                    )
                )
            ]
        }

    nombre_archivo = partes_prefijo[-1].strip("\"'`")
    if (
        not nombre_archivo
        or nombre_archivo in {".", ".."}
        or Path(nombre_archivo).name != nombre_archivo
    ):
        return {
            "messages": [
                AIMessage(
                    content="Indica solo el nombre del archivo, sin incluir su ruta."
                )
            ]
        }

    if contenido.startswith(" "):
        contenido = contenido[1:]
    if not contenido.strip():
        return {
            "messages": [
                AIMessage(
                    content="Incluye el texto que quieres guardar después de los dos puntos."
                )
            ]
        }

    resultado = await ejecutar_herramienta_mcp(
        "guardar_texto",
        {
            "nombre_archivo": nombre_archivo,
            "contenido": contenido
        }
    )

    if isinstance(resultado, list):
        respuesta = "\n".join(
            bloque["text"]
            for bloque in resultado
            if isinstance(bloque, dict)
            and bloque.get("type") == "text"
            and isinstance(bloque.get("text"), str)
        )
    else:
        respuesta = str(resultado)

    return {"messages": [AIMessage(content=respuesta or str(resultado))]}


#  CONSTRUCCIÓN DEL GRAFO

grafo = StateGraph(AgentState)

grafo.add_node("enrutador", nodo_enrutador)
grafo.add_node("matematico", nodo_matematico)
grafo.add_node("poeta", nodo_poeta)
grafo.add_node("cientifico", nodo_cientifico)
grafo.add_node("listar_documentos", nodo_listar_documentos)
grafo.add_node("clasificar_documentos", nodo_clasificar_documentos)
grafo.add_node("copiar_archivos", nodo_copiar_archivos)
grafo.add_node("leer_archivo", nodo_leer_archivo)
grafo.add_node("guardar_texto", nodo_guardar_texto)
grafo.add_edge(START, "enrutador")

def leer_decision(state: AgentState):
    return state["next_agent"]

grafo.add_conditional_edges(
    "enrutador",
    leer_decision,
    {
        "matematico": "matematico",
        "cientifico": "cientifico",
        "listar_documentos": "listar_documentos",
        "clasificar_documentos": "clasificar_documentos",
        "copiar_archivos": "copiar_archivos",
        "leer_archivo": "leer_archivo",
        "guardar_texto": "guardar_texto",
        "poeta": "poeta"
    }
)

grafo.add_edge("matematico", END)
grafo.add_edge("poeta", END)
grafo.add_edge("cientifico", END)
grafo.add_edge("listar_documentos", END)
grafo.add_edge("clasificar_documentos", END)
grafo.add_edge("copiar_archivos", END)
grafo.add_edge("leer_archivo", END)
grafo.add_edge("guardar_texto", END)

app = grafo.compile()


# PRUEBILLAS

# PRUEBAS

async def hacer_pregunta(texto):
    print("\n")
    print(f"Usuario: {texto}")

    inputs = {"messages": [HumanMessage(content=texto)]}

    respuesta_final = await app.ainvoke(inputs)

    print(f"Respuesta Final:\n{respuesta_final['messages'][-1].content}")


async def main():
    while True:
        texto = input("Usuario (o 'salir' para terminar): ").strip()
        if texto.lower() == "salir":
            break
        if texto:
            await hacer_pregunta(texto)


if __name__ == "__main__":
    asyncio.run(main())

