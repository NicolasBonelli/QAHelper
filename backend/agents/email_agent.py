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

MCP_SERVER_URL = os.getenv("MCP_EMAIL_SERVER_URL")
MODEL = os.getenv("MODEL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0, google_api_key=GEMINI_API_KEY)

SELECT_TOOL_PROMPT = """Analiza el mensaje del usuario y selecciona una de estas herramientas:

- draft_professional_email: si el usuario quiere redactar un correo profesional a partir de un mensaje o idea base.
- summarize_email: si el usuario te da un correo largo o cadena de emails para resumir.

Responde con exactamente una línea:

Action: draft_professional_email  
Action: summarize_email

NO escribas nada más.

Mensaje del usuario:
{user_input}"""

# Prompt para ejecutar herramienta de email
EXECUTE_EMAIL_PROMPT = """Eres un asistente especializado en redacción y gestión de correos electrónicos profesionales.

ENTRADA:
-Input del usuario junto con la informacion recuperada {input_block}

TAREA:
Generar una respuesta útil basada en la herramienta seleccionada y el resultado obtenido.

REGLAS:
• Si se usó draft_professional_email: Presenta el correo redactado de forma clara y profesional
• Si se usó summarize_email: Presenta el resumen de manera estructurada y fácil de entender
• Mantén un tono profesional y útil
• No uses tildes en español, escribe todo sin acentos
• Estructura la respuesta de forma clara y organizada
• Si es necesario, ofrece sugerencias adicionales o mejoras

CASOS ESPECIALES:
- Si el correo necesita más detalles: Sugiere información adicional
- Si el resumen es muy largo: Organiza en puntos clave
- Si hay errores en el resultado: Ofrece una versión corregida

Genera una respuesta natural y útil:"""

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
        # Usar directamente DB_URL_LOCAL que ya está en formato SQLAlchemy
        # No necesitamos convertir a psycopg ya que SQLAlchemyChatMessageHistory usa SQLAlchemy
        history = SQLAlchemyChatMessageHistory(session_id=session_id)
        return ConversationBufferMemory(
            chat_memory=history,
            return_messages=True
        )
    except Exception as e:
        print(f"[Email Agent] Error en get_chat_memory: {e}")
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
            print(f"[Email Agent] Nueva sesión creada: {session_id}")
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
        session_id = state.get("session_id")  # asumimos que viene del front
        messages = state.get("messages", [])
        executed_agents = state.get("executed_agents", [])
        
        if not user_input:
            return {"tool_response": "Error: No se recibió input del usuario."}

        print(f"[Email Agent] Procesando: {user_input}")
        print(f"[Email Agent] Agentes ejecutados previamente: {executed_agents}")

        # Paso 1: Obtener herramientas
        try:
            tools = asyncio.run(get_available_tools())
            if not tools:
                # Fallback si no se pueden obtener herramientas
                print("[Email Agent] No se pudieron obtener herramientas, usando herramientas por defecto")
                tools = [
                    {"name": "draft_professional_email", "description": "Redacta correo profesional"},
                    {"name": "summarize_email", "description": "Resume correos largos"}
                ]
            
            tools_str = "\n".join([f"{t['name']}: {t['description']}" for t in tools])
            
            # Paso 2: Usar LLMChain para decidir qué tool usar
            tool_selector = get_tool_selection_chain(llm)
            tool_decision = tool_selector.run(tools=tools_str, user_input=user_input).strip()
            tool_name_raw = tool_decision.strip()
            tool_name = tool_name_raw.replace("Action:", "").strip()
            
            print(f"[Email Agent] Tool seleccionada: {tool_name}")

            # Paso 3: Ejecutar herramienta seleccionada
            # Argumentos mínimos
            if tool_name == "draft_professional_email":
                args = {
                    "to": "soporte@empresa.com",  # o extraer de alguna UI
                    "subject": "Consulta sobre el producto",
                    "body": user_input
                }
            else:
                args = {"text": user_input}

            tool_result = asyncio.run(execute_tool(tool_name, args))
            print(f"[Email Agent] Resultado de tool: {tool_result}")
        except Exception as e:
            print(f"[Email Agent] Error obteniendo/ejecutando herramientas: {e}")
            # Fallback con análisis simple
            if "correo" in user_input.lower() or "email" in user_input.lower() or "redactar" in user_input.lower():
                tool_name = "draft_professional_email"
                tool_result = "Análisis local realizado - Solicitud de redacción de correo detectada"
            else:
                tool_name = "summarize_email"
                tool_result = "Análisis local realizado - Solicitud de resumen detectada"

        # Paso 4: Usar memoria de conversación y LLM para generar respuesta final
        memory = get_chat_memory(session_id)

        agent_prompt = ChatPromptTemplate.from_messages([
            ("system", EXECUTE_EMAIL_PROMPT),
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
        print(f"[Email Agent ERROR] {error_msg}")
        
        # Agregar error al historial
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
            "executed_agents": executed_agents
        }

# Test local
def test_email_agent(query="Hola, quiero escribir un correo al soporte por un problema con la factura, pero no se como redactarlo bien."):
    """Función para probar el agente Email independientemente"""
    print(f"Testing Email Agent with query: {query}")
    
    # UUID específico para la sesión
    session_id = "39105cb8-ba8c-40c6-aaf7-dd8571b605e0"
    
    # Insertar sesión en la base de datos
    insert_chat_session(session_id)
    
    # Simular estado como en LangGraph
    test_state = {"input": query, "session_id": session_id}
    
    result = email_agent_node(test_state)
    
    print(f"Result: {result}")
    return result

if __name__ == "__main__":
    # Test del agente
    test_email_agent("Este es un resumen de tres correos donde se discute el contrato. El primero fue enviado el lunes con detalles legales. El segundo contiene propuestas de fechas. El tercero, una confirmación.")
    test_email_agent("Necesito mandar un correo al equipo de soporte diciendo que no puedo acceder a la plataforma desde ayer.")
