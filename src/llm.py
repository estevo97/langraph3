from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI

def crear_llm(proveedor="ollama", modelo=None):

    if proveedor == "ollama":
        return ChatOllama(
            model=modelo or "llama3.1"
        )

    elif proveedor == "gemini":
        return ChatGoogleGenerativeAI(
            model=modelo or "gemini-3.5-flash-lite"
        )

    else:
        raise ValueError("Proveedor no soportado")