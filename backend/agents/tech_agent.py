from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_core.prompts import ChatPromptTemplate
import os
import asyncio
import nest_asyncio
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.sse import sse_client
import psycopg
from backend.config import DB_URL_LOCAL
from langchain.memory import ConversationBufferMemory
from backend.utils.db_chat_history import SQLAlchemyChatMessageHistory
from backend.models.db import ChatSession
from backend.utils.db_connection import SessionLocal
from uuid import uuid4

nest_asyncio.apply()
load_dotenv(override=True)

# Fix: Use the correct MCP server URL for tech server
MCP_SERVER_URL = os.getenv("MCP_TECH_SERVER_URL")
MODEL = os.getenv("MODEL", "gemini-pro")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0, google_api_key=GEMINI_API_KEY)

# Prompt para selección de herramienta
SELECT_TOOL_PROMPT = """Analiza el siguiente mensaje y selecciona una de estas dos herramientas:

- generate_excel_from_data: si el usuario proporciona datos tabulados o CSV y desea generar un archivo Excel.
- summarize_text: si el usuario proporciona un texto largo y desea obtener un resumen.

Responde con exactamente una línea, en uno de estos dos formatos:

Action: generate_excel_from_data  
Action: summarize_text

NO escribas nada más.

Mensaje del usuario:
{user_input}"""

# Prompt para ejecutar herramienta técnica
EXECUTE_TECH_PROMPT = """Eres un asistente especializado en herramientas técnicas y procesamiento de datos.

ENTRADA:
-Input del usuario junto con la informacion recuperada {input_block}

TAREA:
Generar una respuesta útil basada en la herramienta seleccionada y el resultado obtenido.

REGLAS:
• Si se usó generate_excel_from_data: Explica el archivo generado y cómo acceder a él
• Si se usó summarize_text: Presenta el resumen de manera clara y estructurada
• Mantén un tono técnico pero accesible
• No uses tildes en español, escribe todo sin acentos
• Estructura la respuesta de forma clara y organizada
• Si es necesario, ofrece instrucciones adicionales o sugerencias

CASOS ESPECIALES:
- Si se generó un archivo Excel: Explica dónde encontrarlo y cómo usarlo
- Si el resumen es muy técnico: Simplifica la explicación
- Si hay errores en el procesamiento: Ofrece alternativas o soluciones

Genera una respuesta natural y útil:"""

# Obtener lista de herramientas disponibles desde MCP
async def get_available_tools():
    try:
        print(f"[Tech Agent] Conectando a MCP server: {MCP_SERVER_URL}")
        async with sse_client(f"{MCP_SERVER_URL}/sse") as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools_result = await session.list_tools("list_tools")
                tools = [{"name": tool.name, "description": tool.description} for tool in tools_result.tools]
                print(f"[Tech Agent] Herramientas disponibles: {[t['name'] for t in tools]}")
                return tools
    except Exception as e:
        print(f"Error obteniendo herramientas: {e}")
        # Return default tools if MCP server is not available
        return [
            {"name": "generate_excel_from_data", "description": "Genera archivo Excel desde datos CSV"},
            {"name": "summarize_text", "description": "Resume texto largo"}
        ]

# Ejecutar herramienta seleccionada
async def execute_tool(tool_name: str, arguments: dict):
    try:
        print(f"[Tech Agent] Ejecutando herramienta: {tool_name} con argumentos: {arguments}")
        async with sse_client(f"{MCP_SERVER_URL}/sse") as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=arguments)
                return result.content[0].text if result.content else "No se obtuvo resultado"
    except Exception as e:
        print(f"Error ejecutando herramienta {tool_name}: {e}")
        return f"Error al ejecutar {tool_name}: {str(e)}"

# Chain para decidir qué tool usar
def get_tool_selection_chain(llm):
    prompt = PromptTemplate.from_template(SELECT_TOOL_PROMPT)
    return LLMChain(llm=llm, prompt=prompt)

def get_chat_memory(session_id: str):
    """Devuelve la memoria basada en historial en PostgreSQL"""
    try:
        # Usar directamente DB_URL_LOCAL que ya está en formato SQLAlchemy
        # No necesitamos convertir a psycopg ya que SQLAlchemyChatMessageHistory usa SQLAlchemy
        history = SQLAlchemyChatMessageHistory(session_id=session_id)
        return ConversationBufferMemory(
            chat_memory=history,
            return_messages=True
        )
    except Exception as e:
        print(f"[Tech Agent] Error en get_chat_memory: {e}")
        # Fallback: retornar memoria sin persistencia
        return ConversationBufferMemory(return_messages=True)

def insert_chat_session(session_id: str):
    """Inserta una nueva sesión en la tabla chat_sessions"""
    try:
        db = SessionLocal()
        # Verificar si la sesión ya existe
        existing_session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        
        if not existing_session:
            new_session = ChatSession(id=session_id)
            db.add(new_session)
            db.commit()
            print(f"[Tech Agent] Nueva sesión creada: {session_id}")
        else:
            print(f"[Tech Agent] Sesión ya existe: {session_id}")
        
        db.close()
    except Exception as e:
        print(f"[Tech Agent] Error insertando sesión: {e}")
        if db:
            db.close()

# Nodo principal
def tech_agent_node(state):
    try:
        user_input = state.get("input", "")
        session_id = state.get("session_id")  # asumimos que viene del front
        messages = state.get("messages", [])
        executed_agents = state.get("executed_agents", [])
        
        if not user_input:
            return {"tool_response": "Error: No se recibió input del usuario."}

        print(f"[Tech Agent] Procesando: {user_input}")
        print(f"[Tech Agent] Agentes ejecutados previamente: {executed_agents}")

        # Paso 1: Obtener herramientas
        try:
            tools = asyncio.run(get_available_tools())
            if not tools:
                # Fallback si no se pueden obtener herramientas
                print("[Tech Agent] No se pudieron obtener herramientas, usando herramientas por defecto")
                tools = [
                    {"name": "generate_excel_from_data", "description": "Genera archivo Excel desde datos CSV"},
                    {"name": "summarize_text", "description": "Resume texto largo"}
                ]
            
            tools_str = "\n".join([f"{t['name']}: {t['description']}" for t in tools])
            
            # Paso 2: Usar LLMChain para decidir qué tool usar
            tool_selector = get_tool_selection_chain(llm)
            tool_decision = tool_selector.run(tools=tools_str, user_input=user_input).strip()
            tool_name_raw = tool_decision.strip()
            tool_name = tool_name_raw.replace("Action:", "").strip()
            
            print(f"[Tech Agent] Tool seleccionada: {tool_name}")

            # Paso 3: Ejecutar herramienta seleccionada
            argument_key = "tabla" if tool_name == "generate_excel_from_data" else "text"
            tool_result = asyncio.run(execute_tool(tool_name, {argument_key: user_input}))
            print(f"[Tech Agent] Resultado de tool: {tool_result}")
        except Exception as e:
            print(f"[Tech Agent] Error obteniendo/ejecutando herramientas: {e}")
            # Fallback con análisis simple
            if "csv" in user_input.lower() or "," in user_input or "\n" in user_input:
                tool_name = "generate_excel_from_data"
                tool_result = "Análisis local realizado - Datos tabulados detectados"
            else:
                tool_name = "summarize_text"
                tool_result = "Análisis local realizado - Texto largo detectado"

        # Paso 4: Usar memoria de conversación y LLM para generar respuesta final
        memory = get_chat_memory(session_id)

        agent_prompt = ChatPromptTemplate.from_messages([
            ("system", EXECUTE_TECH_PROMPT),
            ("user", "{input_block}")
        ])
        input_block = f"Input del usuario: {user_input}\n\nResultado de la herramienta: {tool_result}"

        reasoning_chain = LLMChain(llm=llm, prompt=agent_prompt, memory=memory)
        # CORRECCIÓN: usar invoke() y extraer 'text'
        final_output = reasoning_chain.invoke({"input_block": input_block})
        # Robusto: si es string (primera vez), lo usamos directo; si es dict, sacamos solo el texto generado
        if isinstance(final_output, dict):
            final_response = final_output.get("text", str(final_output))
        else:
            final_response = final_output
        
        # Agregar respuesta al historial de mensajes
        messages.append({
            "role": "agent",
            "agent": "tech_agent",
            "content": final_response,
            "timestamp": "tech_response"
        })
        
        return {
            "tool_response": final_response,
            "current_agent": "tech_agent",
            "messages": messages,
            "executed_agents": executed_agents
        }

    except Exception as e:
        error_msg = f"Error en tech_agent_node: {str(e)}"
        print(f"[Tech Agent ERROR] {error_msg}")
        
        # Agregar error al historial
        messages = state.get("messages", [])
        messages.append({
            "role": "agent",
            "agent": "tech_agent",
            "content": error_msg,
            "timestamp": "tech_error"
        })
        
        return {
            "tool_response": error_msg,
            "current_agent": "tech_agent",
            "messages": messages,
            "executed_agents": executed_agents
        }

# Test local
def test_tech_agent(query="nombre,edad,ciudad\nJuan,32,Cordoba\nAna,28,Rosario"):
    """Función para probar el agente Tech independientemente"""
    print(f"Testing Tech Agent with query: {query}")
    
    # UUID específico para la sesión
    session_id = "39105cb8-ba8c-40c6-aaf7-dd8571b605e0"
    
    # Insertar sesión en la base de datos
    insert_chat_session(session_id)
    
    # Simular estado como en LangGraph
    test_state = {"input": query, "session_id": session_id}
    
    result = tech_agent_node(test_state)
    
    print(f"Result: {result}")
    return result

if __name__ == "__main__":
    # Test del agente
    test_tech_agent("nombre,edad\nLucia,25\nPedro,33")
    test_tech_agent("Este es un articulo largo sobre la importancia de la IA en la educación moderna. La IA permite personalizar el aprendizaje y mejorar los resultados educativos. Sin embargo, también plantea desafíos éticos que deben ser abordados...")
