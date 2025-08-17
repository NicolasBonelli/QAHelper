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
from backend.models.db import ChatSession
from backend.utils.db_connection import SessionLocal

nest_asyncio.apply()
load_dotenv(override=True)
import logging

logger = logging.getLogger(__name__)

MCP_SERVER_URL = os.getenv("MCP_EMAIL_SERVER_URL")
MODEL = os.getenv("MODEL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0, google_api_key=GEMINI_API_KEY)

SELECT_TOOL_PROMPT = """Analiza el mensaje del usuario y selecciona una de estas herramientas:

- draft_and_send_email: si el usuario quiere redactar un correo profesional a partir de un mensaje o idea base y enviarlo.

Responde con exactamente una línea:

Action: draft_and_send_email  

NO escribas nada más.

Mensaje del usuario:
{user_input}"""

EXECUTE_EMAIL_PROMPT = """Eres un asistente especializado en redacción y gestión de correos electrónicos profesionales.

ENTRADA:
- Input del usuario junto con la información recuperada {input_block}

TAREA:
- Presentar únicamente el resultado del envío de correo.
- Si el correo fue enviado con éxito: muestra el texto final enviado al destinatario, de forma clara y sin encabezados como "To" o "Subject".
- Si el envío falló: explica brevemente el error y, si aplica, indica cómo corregirlo.
- No respondas ni expliques preguntas adicionales que el usuario haya hecho fuera del contenido del correo.
- No inventes información que no haya sido incluida en el correo.
- No incluyas frases como "El borrador del correo es" o "El correo que redacté es"; muestra directamente el contenido final.

REGLAS:
• Mantén un tono profesional.
• No uses tildes en español (acentos).
• No generes explicaciones sobre temas ajenos al correo.
• Si el remitente no incluyó su nombre, no lo agregues en el saludo.
• La respuesta debe ser únicamente sobre el correo y su estado de envío.
"""
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
        print(f"[Email Agent] Error en get_chat_memory: {e}")
        return ConversationBufferMemory(return_messages=True)

def insert_chat_session(session_id: str):
    """Inserta una nueva sesión en la tabla chat_sessions"""
    try:
        db = SessionLocal()
        existing_session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        
        if not existing_session:
            new_session = ChatSession(id=session_id)
            db.add(new_session)
            db.commit()
        else:
            print(f"[Email Agent] Sesión ya existe: {session_id}")
        
        db.close()
    except Exception as e:
        print(f"[Email Agent] Error insertando sesión: {e}")
        if db:
            db.close()

def email_agent_node(state):
    try:
        user_input = state.get("input", "")
        session_id = state.get("session_id")
        messages = state.get("messages", [])
        executed_agents = state.get("executed_agents", [])
        
        if not user_input:
            return {"tool_response": "Error: No se recibió input del usuario."}

        logger.info(f"[Email Agent] Procesando: {user_input}")
        logger.info(f"[Email Agent] Agentes ejecutados previamente: {executed_agents}")

        try:
            tools = asyncio.run(get_available_tools())
            if not tools:
                print("[Email Agent] No se pudieron obtener herramientas, usando herramientas por defecto")
                tools = [
                    {"name": "draft_and_send_email", "description": "Redacta y envia correo profesional via SMTP"},
                ]
            
            tools_str = "\n".join([f"{t['name']}: {t['description']}" for t in tools])
            
            tool_selector = get_tool_selection_chain(llm)
            tool_decision = tool_selector.run(tools=tools_str, user_input=user_input).strip()
            tool_name_raw = tool_decision.strip()
            tool_name = tool_name_raw.replace("Action:", "").strip()
            
            logger.info(f"[Email Agent] Tool seleccionada: {tool_name}")


            if tool_name == "draft_and_send_email":
  
                args = {
                    "from_person": session_id,  
                    "subject": "Consulta profesional",     
                    "body": user_input
                }
            else:
                args = {"text": user_input}

            tool_result = asyncio.run(execute_tool(tool_name, args))
            logger.info(f"[Email Agent] Resultado de tool: {tool_result}")
        except Exception as e:
            logger.info(f"[Email Agent] Error obteniendo/ejecutando herramientas: {e}")
            if "correo" in user_input.lower() or "email" in user_input.lower() or "redactar" in user_input.lower():
                tool_name = "draft_and_send_email"
                tool_result = "Análisis local realizado - Solicitud de redacción de correo detectada"
            else:
                tool_name = "draft_and_send_email"
                tool_result = "Análisis local realizado - Procesando solicitud de email"

        memory = get_chat_memory(session_id)

        agent_prompt = ChatPromptTemplate.from_messages([
            ("system", EXECUTE_EMAIL_PROMPT),
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
            "agent": "email_agent",
            "content": final_response,
            "timestamp": "email_response"
        })
        
        return {
            "tool_response": final_response,
            "current_agent": "email_agent",
            "messages": messages,
            "executed_agents": executed_agents
        }

    except Exception as e:
        error_msg = f"Error en email_agent_node: {str(e)}"
        logger.warning(f"[Email Agent ERROR] {error_msg}")
        
        messages = state.get("messages", [])
        messages.append({
            "role": "agent",
            "agent": "email_agent",
            "content": error_msg,
            "timestamp": "email_error"
        })
        
        return {
            "tool_response": error_msg,
            "current_agent": "email_agent",
            "messages": messages,
            "executed_agents": state.get("executed_agents", [])
        }


