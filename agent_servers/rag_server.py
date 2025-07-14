from fastmcp import FastMCP
from fastapi import APIRouter
from pydantic import BaseModel
from fastapi import FastAPI

# Configuración MCP sin parámetros obsoletos
mcp = FastMCP(
    name="rag_agent",
    instructions="Servidor MCP con herramientas dinámicas",
    host = "0.0.0.0",
    port = 8050
)


# Modelo para la respuesta de herramientas

# Herramientas implementadas
@mcp.tool
def search_documents(query: str):
    """Busca en los documentos para resumenes sobre ciertos aspectos de los productos de la empresa. Argumentos: query:str"""
    return f"Resultados para '{query}':\n- Doc 1\n- Doc 2"

@mcp.tool
def faq_query(query: str):
    """Responde FAQs sobre la empresa. Argumentos: question:str"""
    horario=" Horario de atencion de 8 am a 5 pm"
    return horario


if __name__ == "__main__":
    mcp.run(transport="sse")

    