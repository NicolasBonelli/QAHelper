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

nest_asyncio.apply()
load_dotenv(override=True)
logger = logging.getLogger(__name__)

MCP_SERVER_URL = os.getenv("MCP_TECH_SERVER_URL")
MODEL = os.getenv("MODEL", "gemini-pro")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0, google_api_key=GEMINI_API_KEY)

SELECT_TOOL_PROMPT = """Analiza el siguiente mensaje y selecciona una de estas dos herramientas:

- generate_excel_from_data: si el usuario proporciona datos tabulados o CSV y desea generar un archivo Excel.
- summarize_text: si el usuario proporciona un texto largo y desea obtener un resumen.

Responde con exactamente una línea, en uno de estos dos formatos:

Action: generate_excel_from_data  
Action: summarize_text

NO escribas nada más.

Mensaje del usuario:
{user_input}"""

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

async def get_available_tools():
    try:
        async with sse_client(f"{MCP_SERVER_URL}/sse") as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools_result = await session.list_tools("list_tools")
                tools = [{"name": tool.name, "description": tool.description} for tool in tools_result.tools]
                return tools
    except Exception as e:
        logger.info(f"Error obteniendo herramientas: {e}")
        return [
            {"name": "generate_excel_from_data", "description": "Genera archivo Excel desde datos CSV"},
            {"name": "summarize_text", "description": "Resume texto largo"}
        ]

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
        logger.info(f"[Tech Agent] Error en get_chat_memory: {e}")
        return ConversationBufferMemory(return_messages=True)



def tech_agent_node(state):
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
                logger.info("[Tech Agent] No se pudieron obtener herramientas, usando herramientas por defecto")
                tools = [
                    {"name": "generate_excel_from_data", "description": "Genera archivo Excel desde datos CSV"},
                    {"name": "summarize_text", "description": "Resume texto largo"}
                ]
            
            tools_str = "\n".join([f"{t['name']}: {t['description']}" for t in tools])
            
            tool_selector = get_tool_selection_chain(llm)
            tool_decision = tool_selector.run(tools=tools_str, user_input=user_input).strip()
            tool_name_raw = tool_decision.strip()
            tool_name = tool_name_raw.replace("Action:", "").strip()
            
            logger.info(f"[Tech Agent] Tool seleccionada: {tool_name}")

            argument_key = "tabla" if tool_name == "generate_excel_from_data" else "text"
            tool_result = asyncio.run(execute_tool(tool_name, {argument_key: user_input}))
            logger.info(f"[Tech Agent] Resultado de tool: {tool_result}")
        except Exception as e:
            logger.info(f"[Tech Agent] Error obteniendo/ejecutando herramientas: {e}")
            if "csv" in user_input.lower() or "," in user_input or "\n" in user_input:
                tool_name = "generate_excel_from_data"
                tool_result = "Análisis local realizado - Datos tabulados detectados"
            else:
                tool_name = "summarize_text"
                tool_result = "Análisis local realizado - Texto largo detectado"

        memory = get_chat_memory(session_id)

        agent_prompt = ChatPromptTemplate.from_messages([
            ("system", EXECUTE_TECH_PROMPT),
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
        logger.warning(f"[Tech Agent ERROR] {error_msg}")
        
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


