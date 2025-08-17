from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv
import asyncio
import nest_asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from utils.db_chat_history import SQLAlchemyChatMessageHistory
import logging

logger = logging.getLogger(__name__)


nest_asyncio.apply()
load_dotenv(override=True)

MCP_SERVER_URL= os.getenv("MCP_RAG_SERVER_URL")
MODEL = os.getenv("MODEL")

SELECT_TOOL_PROMPT  = """Eres un asistente que debe elegir la mejor herramienta para resolver la pregunta del usuario. 
Herramientas disponibles: 
{tools}

Analiza la pregunta y responde SOLO con el nombre de la herramienta adecuada. Ejemplo:
Action: search_documents"""

EXECUTE_TOOL_PROMPT = """Eres un asistente especializado en proporcionar respuestas basadas en información recuperada de documentos y bases de conocimiento.

ENTRADA:
-Input del usuario junto con la informacion recuperada {input_block}

TAREA:
Generar una respuesta completa y útil basándote exclusivamente en la información proporcionada.

REGLAS:
• Responde SOLO con información presente en el resultado de la herramienta
• Si la información es insuficiente, indícalo claramente: "No encontré información suficiente sobre..."
• Mantén un tono conversacional y profesional
• Estructura la respuesta de forma clara y organizada
• Cita o referencia la fuente cuando sea relevante
• Si no hay resultados, ofrece alternativas: "Podrías intentar preguntar sobre..."
• No pongas tildes en español , deja todo sin tilde como por ejemplo informacion sin tilde en la "o"

CASOS ESPECIALES:
- Si el tool_result contiene múltiples documentos: Resume los puntos clave
- Si el tool_result es un error: Explica amablemente que no se pudo acceder a la información
- Si la pregunta es muy específica y no hay match exacto: Ofrece la información más cercana disponible

Genera una respuesta natural y útil:"""

llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0,google_api_key=os.getenv("GEMINI_API_KEY"))
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
        logger.info(f"Error obteniendo herramientas: {e}")
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
        logger.info(f"Error ejecutando herramienta {tool_name}: {e}")
        return f"Error al ejecutar {tool_name}: {str(e)}"


def get_tools_sync():
    """Wrapper síncrono para obtener herramientas"""
    return asyncio.run(get_available_tools())

def execute_tool_sync(tool_name: str, arguments: dict):
    """Wrapper síncrono para ejecutar herramienta"""
    return asyncio.run(execute_tool(tool_name, arguments))


def get_tool_selection_chain(llm):
    prompt = PromptTemplate.from_template(
        SELECT_TOOL_PROMPT  
    )
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
        logger.info(f"[Rag Agent] Error en get_chat_memory: {e}")
        return ConversationBufferMemory(return_messages=True)



def rag_agent_node(state):
    try:
        user_input = state.get("input", "")
        session_id = state.get("session_id")  
        messages = state.get("messages", [])
        executed_agents = state.get("executed_agents", [])

        if not user_input:
            return {"tool_response": "Error: No se recibió input del usuario."}


        tools = asyncio.run(get_available_tools())

        tools_str = "\n".join([f"{t['name']}: {t['description']}" for t in tools])

        tool_selector = get_tool_selection_chain(llm)
        tool_decision = tool_selector.run(tools=tools_str, user_input=user_input).strip()
        tool_name_raw = tool_decision.strip()
        tool_name = tool_name_raw.replace("Action:", "").strip()

        
        tool_result = asyncio.run(execute_tool(tool_name, {"query": user_input}))

        memory = get_chat_memory(session_id)

        agent_prompt = ChatPromptTemplate.from_messages([
            ("system", EXECUTE_TOOL_PROMPT),
            ("user", "{input_block}")
        ])
        input_block = f"Consulta: {user_input}\n\nInformación recuperada:\n{tool_result}"

        reasoning_chain = LLMChain(llm=llm, prompt=agent_prompt, memory=memory)
        final_output = reasoning_chain.invoke({"input_block": input_block})

        if isinstance(final_output, dict):
            final_response = final_output.get("text", str(final_output))
        else:
            final_response = final_output

        messages.append({
            "role": "agent",
            "agent": "rag_agent",
            "content": final_response,
            "timestamp": "rag_response"
        })

        return {
            "tool_response": final_response,
            "current_agent": "rag_agent",
            "messages": messages,
            "executed_agents": executed_agents
        }

    except Exception as e:
        error_msg = f"Error en rag_agent_node: {str(e)}"
        logger.warning(f"[RAG Agent ERROR] {error_msg}")
        
        messages = state.get("messages", [])
        messages.append({
            "role": "agent",
            "agent": "rag_agent",
            "content": error_msg,
            "timestamp": "rag_error"
        })
        
        return {
            "tool_response": error_msg,
            "current_agent": "rag_agent",
            "messages": messages,
            "executed_agents": executed_agents
        }

