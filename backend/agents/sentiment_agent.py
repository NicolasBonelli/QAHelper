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
from langchain.memory import ConversationBufferMemory
from backend.utils.db_chat_history import SQLAlchemyChatMessageHistory
from backend.utils.db_actions import insert_chat_session
import logging

logger = logging.getLogger(__name__)

nest_asyncio.apply()
load_dotenv(override=True)

MCP_SERVER_URL = os.getenv("MCP_SENTIMENT_SERVER_URL")
MODEL = os.getenv("MODEL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0, google_api_key=GEMINI_API_KEY)

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

async def get_available_tools():
    try:
        async with sse_client(f"{MCP_SERVER_URL}/sse") as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools_result = await session.list_tools("list_tools")
                return [{"name": tool.name, "description": tool.description} for tool in tools_result.tools]
    except Exception as e:
        logger.info(f"Error obteniendo herramientas: {e}")
        return []

async def execute_tool(tool_name: str, arguments: dict):
    try:
        async with sse_client(f"{MCP_SERVER_URL}/sse") as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=arguments)
                return result.content[0].text if result.content else "No se obtuvo resultado"
    except Exception as e:
        logger.info(f"Error ejecutando herramienta {tool_name}: {e}")
        return f"Error al ejecutar {tool_name}: {str(e)}"

def get_tool_selection_chain(llm):
    prompt = PromptTemplate.from_template(SELECT_TOOL_PROMPT)
    return LLMChain(llm=llm, prompt=prompt)

def get_chat_memory(session_id: str):
    """Devuelve la memoria basada en historial en PostgreSQL"""
    try:
        history = SQLAlchemyChatMessageHistory(session_id=session_id,persist=False)
        return ConversationBufferMemory(
            chat_memory=history,
            return_messages=True
        )
    except Exception as e:
        logger.info(f"[Sentiment Agent] Error en get_chat_memory: {e}")
        return ConversationBufferMemory(return_messages=True)



def sentiment_agent_node(state):
    try:
        user_input = state.get("input", "")
        session_id = state.get("session_id")  
        messages = state.get("messages", [])
        executed_agents = state.get("executed_agents", [])
        
        if not user_input:
            return {"tool_response": "Error: No se recibió input del usuario."}

        try:
            tools = asyncio.run(get_available_tools())
            if not tools:
                logger.info("[Sentiment Agent] No se pudieron obtener herramientas, usando análisis local")
                offensive_words = ["mierda", "pelotudo", "imbecil", "inutiles", "asco", "horrible", "hdp", "estafa"]
                has_offensive = any(word in user_input.lower() for word in offensive_words)
                tool_name = "warn_or_ban_user" if has_offensive else "calm_down_user"
                tool_result = "Análisis local realizado - " + ("Lenguaje inapropiado detectado" if has_offensive else "Frustración detectada")
            else:
                tools_str = "\n".join([f"{t['name']}: {t['description']}" for t in tools])
                
                tool_selector = get_tool_selection_chain(llm)
                tool_decision = tool_selector.run(tools=tools_str, user_input=user_input).strip()
                tool_name_raw = tool_decision.strip()
                tool_name = tool_name_raw.replace("Action:", "").strip()
                

                tool_result = asyncio.run(execute_tool(tool_name, {"text": user_input}))
                logger.info(f"[Sentiment Agent] Resultado de tool: {tool_result}")
        except Exception as e:
            logger.info(f"[Sentiment Agent] Error obteniendo/ejecutando herramientas: {e}")
            offensive_words = ["mierda", "pelotudo", "imbecil", "inutiles", "asco", "horrible", "hdp", "estafa"]
            has_offensive = any(word in user_input.lower() for word in offensive_words)
            tool_name = "warn_or_ban_user" if has_offensive else "calm_down_user"
            tool_result = "Análisis local realizado - " + ("Lenguaje inapropiado detectado" if has_offensive else "Frustración detectada")

        memory = get_chat_memory(session_id)

        agent_prompt = ChatPromptTemplate.from_messages([
            ("system", EXECUTE_SENTIMENT_PROMPT),
            ("user", "{input_block}")
        ])
        input_block = f"Input del usuario: {user_input}\n\nResultado de la herramienta: {tool_result}"

        reasoning_chain = LLMChain(llm=llm, prompt=agent_prompt, memory=memory)
        final_output = reasoning_chain.invoke({"input_block": input_block})
        if isinstance(final_output, dict):
            final_response = final_output.get("text", str(final_output))
        else:
            final_response = final_output
        
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
        logger.warning(f"[Sentiment Agent ERROR] {error_msg}")
        
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

