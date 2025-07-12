from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
import requests
from agent_servers.utils.mcp_dynamic_adapter import MCPDynamicAdapter
import os
from dotenv import load_dotenv
import asyncio
import nest_asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

nest_asyncio.apply()
load_dotenv()
MCP_SERVER_URL = os.getenv("MCP_RAG_SERVER_URL")

MODEL = os.getenv("MODEL")

# Prompt mejorado para el agente RAG
SELECT_TOOL_PROMPT  = """Eres un asistente que debe elegir la mejor herramienta para resolver la pregunta del usuario. 
Herramientas disponibles: 
{tools}

Analiza la pregunta y responde SOLO con el nombre de la herramienta adecuada. Ejemplo:
Action: search_documents"""

EXECUTE_TOOL_PROMPT = """Eres un asistente especializado en proporcionar respuestas basadas en información recuperada de documentos y bases de conocimiento.

ENTRADA:
- Consulta del usuario: {user_input}
- Información recuperada: {tool_result}

TAREA:
Generar una respuesta completa y útil basándote exclusivamente en la información proporcionada.

REGLAS:
• Responde SOLO con información presente en el resultado de la herramienta
• Si la información es insuficiente, indícalo claramente: "No encontré información suficiente sobre..."
• Mantén un tono conversacional y profesional
• Estructura la respuesta de forma clara y organizada
• Cita o referencia la fuente cuando sea relevante
• Si no hay resultados, ofrece alternativas: "Podrías intentar preguntar sobre..."

CASOS ESPECIALES:
- Si el tool_result contiene múltiples documentos: Resume los puntos clave
- Si el tool_result es un error: Explica amablemente que no se pudo acceder a la información
- Si la pregunta es muy específica y no hay match exacto: Ofrece la información más cercana disponible

Genera una respuesta natural y útil:"""

llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0)
adapter = MCPDynamicAdapter(MCP_SERVER_URL)
# Funciones para interactuar con MCP Server
async def get_available_tools():
    """Obtiene todas las herramientas disponibles del servidor MCP"""
    try:
        async with sse_client(f"{MCP_SERVER_URL}/sse") as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                
                tools_result = await session.list_tools("list_tools")
                tools_info = []
                
                for tool in tools_result.tools:
                    tools_info.append({
                        "name": tool.name,
                        "description": tool.description
                    })
                
                return tools_info
                
    except Exception as e:
        print(f"Error obteniendo herramientas: {e}")
        return []
    
async def execute_tool(tool_name: str, arguments: dict):
    """Ejecuta una herramienta específica con los argumentos dados"""
    try:
        async with sse_client(f"{MCP_SERVER_URL}/sse") as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                
                result = await session.call_tool(tool_name, arguments=arguments)
                return result.content[0].text if result.content else "No se obtuvo resultado"
                
    except Exception as e:
        print(f"Error ejecutando herramienta {tool_name}: {e}")
        return f"Error al ejecutar {tool_name}: {str(e)}"


def get_tools_sync():
    """Wrapper síncrono para obtener herramientas"""
    return asyncio.run(get_available_tools())

def execute_tool_sync(tool_name: str, arguments: dict):
    """Wrapper síncrono para ejecutar herramienta"""
    return asyncio.run(execute_tool(tool_name, arguments))



def get_agent_executor():
    """Crea y retorna el ejecutor del agente con las herramientas MCP"""
    try:
        tools = adapter.load_tools()
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("user", "{input}"),
            MessagesPlaceholder("agent_scratchpad")
        ])
        
        agent = create_tool_calling_agent(llm, tools, prompt)
        return AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)
    except Exception as e:
        print(f"Error creando agent executor: {e}")
        return None
    


def process_user_query(user_input: str) -> str:
    """Procesa la consulta del usuario usando el agente RAG"""
    try:
        # Verifica conexión al servidor MCP
        if not check_mcp_connection():
            return "Error: No se puede conectar al servidor MCP. Verifica que el servidor esté ejecutándose."
            
        executor = get_agent_executor()
        if not executor:
            return "Error: No se pudo crear el agente ejecutor."
            
        result = executor.invoke({"input": user_input})
        return result.get("output", "No se pudo procesar la consulta.")
        
    except Exception as e:
        print(f"Error procesando consulta: {e}")
        return f"Error interno: {str(e)}"

def check_mcp_connection() -> bool:
    """Verifica que el servidor MCP esté disponible"""
    try:
        response = requests.get(f"{MCP_SERVER_URL}/health", timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"Error verificando conexión MCP: {e}")
        return False

# NODO PRINCIPAL PARA LANGGRAPH
def rag_agent_node(state):
    """
    Nodo del agente RAG para LangGraph.
    
    Recibe el estado con:
    - input: consulta del usuario
    
    Retorna:
    - tool_response: respuesta procesada del agente
    """
    try:
        user_input = state.get("input", "")
        
        if not user_input:
            return {"tool_response": "Error: No se recibió input del usuario."}
        
        print(f"[RAG Agent] Procesando: {user_input}")
        
        # Procesar la consulta usando el agente RAG
        response = process_user_query(user_input)
        
        print(f"[RAG Agent] Respuesta generada: {response}")
        
        return {"tool_response": response}
        
    except Exception as e:
        error_msg = f"Error en rag_agent_node: {str(e)}"
        print(f"[RAG Agent ERROR] {error_msg}")
        return {"tool_response": error_msg}

# Función de utilidad para testing
def test_rag_agent(query: str = "¿Cuál es el horario de atención?"):
    """Función para probar el agente RAG independientemente"""
    print(f"Testing RAG Agent with query: {query}")
    
    # Simular estado como en LangGraph
    test_state = {"input": query}
    result = rag_agent_node(test_state)
    
    print(f"Result: {result}")
    return result

if __name__ == "__main__":
    # Test del agente
    test_rag_agent("¿Cuál es el horario de atención?")
    test_rag_agent("Busca información sobre perros")