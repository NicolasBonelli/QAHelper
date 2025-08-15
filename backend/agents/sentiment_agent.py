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
from config import DB_URL_LOCAL
from langchain.memory import ConversationBufferMemory
from utils.db_chat_history import SQLAlchemyChatMessageHistory
from utils.db_actions import insert_chat_session
from uuid import uuid4

nest_asyncio.apply()
load_dotenv(override=True)

MCP_SERVER_URL = os.getenv("MCP_SENTIMENT_SERVER_URL")
MODEL = os.getenv("MODEL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0, google_api_key=GEMINI_API_KEY)

# Prompt para selección de herramienta
SELECT_TOOL_PROMPT = """Analiza el siguiente mensaje de un usuario y selecciona una de estas dos herramientas:

- calm_down_user: si el mensaje refleja enojo o frustración pero sin insultos ni lenguaje ofensivo.
- warn_or_ban_user: si el mensaje contiene insultos, groserías o un tono muy agresivo.

Considera como insultos palabras como: "mierda", "pelotudo", "imbecil", "inutiles", "asco", "horrible", "hdp", "estafa", etc.

Responde con exactamente una línea, en uno de estos dos formatos:

Action: calm_down_user  
Action: warn_or_ban_user

NO escribas nada más.

Mensaje del usuario:
{user_input}"""

# Prompt para ejecutar herramienta de sentimiento
EXECUTE_SENTIMENT_PROMPT = """Eres un asistente especializado en moderación de contenido y manejo de sentimientos de usuarios.

ENTRADA:
-Input del usuario junto con la informacion recuperada {input_block}

TAREA:
Generar una respuesta apropiada basada en el análisis de sentimiento y la herramienta seleccionada.

REGLAS:
• Si se usó calm_down_user: Responde con empatía y calma, ofreciendo ayuda
• Si se usó warn_or_ban_user: Responde de manera firme pero profesional, explicando las consecuencias
• Mantén un tono profesional y constructivo
• No uses tildes en español, escribe todo sin acentos
• Estructura la respuesta de forma clara y organizada
• Si es necesario, ofrece alternativas o soluciones

CASOS ESPECIALES:
- Si el usuario está frustrado: Ofrece ayuda específica
- Si el usuario usa lenguaje inapropiado: Explica las políticas de la plataforma
- Si es un malentendido: Aclara la situacion de manera amigable

Genera una respuesta natural y apropiada:"""

# Obtener lista de herramientas disponibles desde MCP
async def get_available_tools():
    try:
        async with sse_client(f"{MCP_SERVER_URL}/sse") as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools_result = await session.list_tools("list_tools")
                return [{"name": tool.name, "description": tool.description} for tool in tools_result.tools]
    except Exception as e:
        print(f"Error obteniendo herramientas: {e}")
        return []

# Ejecutar herramienta seleccionada
async def execute_tool(tool_name: str, arguments: dict):
    try:
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
        history = SQLAlchemyChatMessageHistory(session_id=session_id,persist=False)
        return ConversationBufferMemory(
            chat_memory=history,
            return_messages=True
        )
    except Exception as e:
        print(f"[Sentiment Agent] Error en get_chat_memory: {e}")
        # Fallback: retornar memoria sin persistencia
        return ConversationBufferMemory(return_messages=True)



# Nodo principal para LangGraph
def sentiment_agent_node(state):
    try:
        user_input = state.get("input", "")
        session_id = state.get("session_id")  # asumimos que viene del front
        messages = state.get("messages", [])
        executed_agents = state.get("executed_agents", [])
        
        if not user_input:
            return {"tool_response": "Error: No se recibió input del usuario."}

        print(f"[Sentiment Agent] Procesando: {user_input}")
        print(f"[Sentiment Agent] Agentes ejecutados previamente: {executed_agents}")

        # Paso 1: Obtener herramientas
        try:
            tools = asyncio.run(get_available_tools())
            if not tools:
                # Fallback si no se pueden obtener herramientas
                print("[Sentiment Agent] No se pudieron obtener herramientas, usando análisis local")
                # Análisis simple local basado en palabras clave
                offensive_words = ["mierda", "pelotudo", "imbecil", "inutiles", "asco", "horrible", "hdp", "estafa"]
                has_offensive = any(word in user_input.lower() for word in offensive_words)
                tool_name = "warn_or_ban_user" if has_offensive else "calm_down_user"
                tool_result = "Análisis local realizado - " + ("Lenguaje inapropiado detectado" if has_offensive else "Frustración detectada")
            else:
                tools_str = "\n".join([f"{t['name']}: {t['description']}" for t in tools])
                
                # Paso 2: Usar LLMChain para decidir qué tool usar
                tool_selector = get_tool_selection_chain(llm)
                tool_decision = tool_selector.run(tools=tools_str, user_input=user_input).strip()
                tool_name_raw = tool_decision.strip()
                tool_name = tool_name_raw.replace("Action:", "").strip()
                
                print(f"[Sentiment Agent] Tool seleccionada: {tool_name}")

                # Paso 3: Ejecutar herramienta seleccionada
                tool_result = asyncio.run(execute_tool(tool_name, {"text": user_input}))
                print(f"[Sentiment Agent] Resultado de tool: {tool_result}")
        except Exception as e:
            print(f"[Sentiment Agent] Error obteniendo/ejecutando herramientas: {e}")
            # Fallback con análisis simple
            offensive_words = ["mierda", "pelotudo", "imbecil", "inutiles", "asco", "horrible", "hdp", "estafa"]
            has_offensive = any(word in user_input.lower() for word in offensive_words)
            tool_name = "warn_or_ban_user" if has_offensive else "calm_down_user"
            tool_result = "Análisis local realizado - " + ("Lenguaje inapropiado detectado" if has_offensive else "Frustración detectada")

        # Paso 4: Usar memoria de conversación y LLM para generar respuesta final
        memory = get_chat_memory(session_id)

        agent_prompt = ChatPromptTemplate.from_messages([
            ("system", EXECUTE_SENTIMENT_PROMPT),
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
            "agent": "sentiment_agent",
            "content": final_response,
            "timestamp": "sentiment_response"
        })
        
        return {
            "tool_response": final_response,
            "current_agent": "sentiment_agent",
            "messages": messages,
            "executed_agents": executed_agents
        }

    except Exception as e:
        error_msg = f"Error en sentiment_agent_node: {str(e)}"
        print(f"[Sentiment Agent ERROR] {error_msg}")
        
        # Agregar error al historial
        messages = state.get("messages", [])
        messages.append({
            "role": "agent",
            "agent": "sentiment_agent",
            "content": error_msg,
            "timestamp": "sentiment_error"
        })
        
        return {
            "tool_response": error_msg,
            "current_agent": "sentiment_agent",
            "messages": messages,
            "executed_agents": executed_agents
        }

# Test local
def test_sentiment_agent(query="Esto es una mierda, no pienso usar mas esta app."):
    """Función para probar el agente Sentiment independientemente"""
    print(f"Testing Sentiment Agent with query: {query}")
    
    # UUID específico para la sesión
    session_id = "39105cb8-ba8c-40c6-aaf7-dd8571b605e0"
    
    # Insertar sesión en la base de datos
    insert_chat_session(session_id)
    
    # Simular estado como en LangGraph
    test_state = {"input": query, "session_id": session_id}
    
    result = sentiment_agent_node(test_state)
    
    print(f"Result: {result}")
    return result

if __name__ == "__main__":
    # Test del agente
    test_sentiment_agent("Esta app es lo peor que vi, un asco, nunca responden.")
   # test_sentiment_agent("Estoy un poco molesto con el tiempo de espera.")
  # test_sentiment_agent("Nunca me responden nada de lo que hago, esto está muy mal.")
