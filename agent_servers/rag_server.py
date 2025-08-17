from fastmcp import FastMCP
from langsmith import traceable
import sys
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv(override=True)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.utils.llamaindex_utils import retrieve_chunks
MODEL = os.getenv("MODEL")

mcp = FastMCP(
    name="rag_agent",
    instructions="Servidor MCP con herramientas dinamicas para RAG (Retrieval Augmented Generation) usando base de datos PostgreSQL",
    host = "0.0.0.0",
    port = 8050
)

@traceable(run_type="retriever", name="retrieve_chunks_from_db")
def traced_retrieve_chunks(query: str, k: int = 5):
    """
    Recupera chunks y los retorna en formato compatible con LangSmith para visualizacion.
    """
    top_chunks = retrieve_chunks(query, k)
    return [
        {
            "page_content": chunk.text,
            "type": "Document",
            "metadata": getattr(chunk, "metadata", {})
        }
        for chunk in top_chunks
    ]

@mcp.tool
@traceable(run_type="tool", name="search_documents")
def search_documents(query: str):
    """Busca en los documentos para resumenes sobre ciertos aspectos de los productos de la empresa. Argumentos: query:str"""
    return f"Resultados para '{query}':\n- Doc 1\n- Doc 2"


@mcp.tool
@traceable(run_type="tool", name="faq_query")
def faq_query(query: str) -> str:
    """
    Herramienta RAG avanzada que recupera los 5 chunks mas relevantes desde la base de datos,
    los pasa como contexto a Gemini y genera una respuesta final usando LangChain.
    Argumentos: query:str
    """
    try:
        retrieved_docs = traced_retrieve_chunks(query, 5)
        
        if not retrieved_docs:
            return "No se encontraron documentos relevantes para tu consulta."
        
        context_text = "\n\n".join([doc["page_content"] for doc in retrieved_docs])
        
        prompt_template = ChatPromptTemplate.from_template("""
        Eres un asistente experto en la empresa. Responde de manera clara, concisa y util 
        a la siguiente pregunta del usuario basandote exclusivamente en la informacion 
        proporcionada en el contexto.

        Si no hay suficiente informacion para responder, indicalo claramente sin inventar datos.

        ---
        Contexto:
        {context}

        Pregunta del usuario:
        {query}

        Respuesta:
        """)
        
        llm = ChatGoogleGenerativeAI(
            model=MODEL,
            temperature=0,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        
        chain = prompt_template | llm
        gemini_response = chain.invoke({"context": context_text, "query": query})
        
        return gemini_response.content.strip()
        
    except Exception as e:
        return f"Error en el procesamiento RAG: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="sse")