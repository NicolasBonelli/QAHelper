from fastmcp import FastMCP
from fastapi import APIRouter
from pydantic import BaseModel
from fastapi import FastAPI
from langsmith import traceable
import sys
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.utils.llamaindex_utils import retrieve_chunks
load_dotenv(override=True)
MODEL = os.getenv("MODEL")

# Configuración MCP sin parámetros obsoletos
mcp = FastMCP(
    name="rag_agent",
    instructions="Servidor MCP con herramientas dinámicas para RAG (Retrieval Augmented Generation) usando base de datos PostgreSQL",
    host = "0.0.0.0",
    port = 8050
)

# Herramientas implementadas
@mcp.tool
@traceable(run_type="tool", name="search_documents")
def search_documents(query: str):
    """Busca en los documentos para resumenes sobre ciertos aspectos de los productos de la empresa. Argumentos: query:str"""
    return f"Resultados para '{query}':\n- Doc 1\n- Doc 2"


from langchain.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

@mcp.tool
@traceable(run_type="tool", name="faq_query")
def faq_query(query: str) -> str:
    """
    Herramienta RAG avanzada que recupera los 5 chunks más relevantes desde la base de datos,
    los pasa como contexto a Gemini y genera una respuesta final usando LangChain.
    Argumentos: query:str
    """
    try:
        # 1. Obtener los top 5 chunks más relevantes
        top_chunks = retrieve_chunks(query,  5)
        
        if not top_chunks:
            return "No se encontraron documentos relevantes para tu consulta."
        
        # 2. Unir todos los chunks en un solo texto de contexto
        context_text = "\n\n".join([chunk.text for chunk in top_chunks])
        
        # 3. Crear el prompt con LangChain
        prompt_template = ChatPromptTemplate.from_template("""
        Eres un asistente experto en la empresa. Responde de manera clara, concisa y útil 
        a la siguiente pregunta del usuario basándote exclusivamente en la información 
        proporcionada en el contexto.

        Si no hay suficiente información para responder, indícalo claramente sin inventar datos.

        ---
        Contexto:
        {context}

        Pregunta del usuario:
        {query}

        Respuesta:
        """)
        
        # 4. Crear el modelo Gemini
        llm = ChatGoogleGenerativeAI(
            model=MODEL,  # Puedes cambiar por el modelo que prefieras
            temperature=0,
            google_api_key=os.getenv("GOOGLE_API_KEY")

        )
        
        # 5. Ejecutar la cadena
        chain = prompt_template | llm
        gemini_response = chain.invoke({"context": context_text, "query": query})
        
        # 6. Retornar la respuesta de Gemini
        return gemini_response.content.strip()
        
    except Exception as e:
        return f"Error en el procesamiento RAG: {str(e)}"


if __name__ == "__main__":
    print("🚀 Iniciando servidor RAG MCP en puerto 8050...")
    mcp.run(transport="sse")

    