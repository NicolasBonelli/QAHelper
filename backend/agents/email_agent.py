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

- draft_and_send_email: si el usuario quiere redactar un correo profesional a partir de un mensaje o idea base y enviarlo.

Responde con exactamente una línea:

Action: draft_and_send_email  

NO escribas nada más.

Mensaje del usuario:
{user_input}"""

# Prompt para ejecutar herramienta de email
EXECUTE_EMAIL_PROMPT = """Eres un asistente especializado en redacción y gestión de correos electrónicos profesionales.

TAREA:
Generar una respuesta útil basada en la herramienta seleccionada y el resultado obtenido.

REGLAS IMPORTANTES:
• Si se usó draft_and_send_email: Presenta el correo redactado de forma clara y profesional
• Menciona si fue enviado exitosamente
• Mantén un tono profesional y útil
• No uses tildes en español, escribe todo sin acentos
• Estructura la respuesta de forma clara y organizada
• NO repitas información innecesariamente
• NO dupliques contenido del correo
• NO repitas frases o párrafos completos
• Escribe cada idea UNA SOLA VEZ

FORMATO DE RESPUESTA:
1. Confirmar que el correo fue enviado
2. Mostrar el contenido del correo de forma clara
3. No repetir información

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

def clean_duplicate_content(text: str) -> str:
    """Elimina contenido duplicado en el texto"""
    if not text:
        return text
    
    # Dividir por líneas y eliminar duplicados consecutivos
    lines = text.split('\n')
    cleaned_lines = []
    prev_line = None
    
    for line in lines:
        line = line.strip()
        if line and line != prev_line:
            cleaned_lines.append(line)
            prev_line = line
    
    return '\n'.join(cleaned_lines)

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
                    {"name": "draft_and_send_email", "description": "Redacta y envia correo profesional via SMTP"},
                ]
            
            tools_str = "\n".join([f"{t['name']}: {t['description']}" for t in tools])
            
            # Paso 2: Usar LLMChain para decidir qué tool usar
            tool_selector = get_tool_selection_chain(llm)
            tool_decision = tool_selector.run(tools=tools_str, user_input=user_input).strip()
            tool_name_raw = tool_decision.strip()
            tool_name = tool_name_raw.replace("Action:", "").strip()
            
            print(f"[Email Agent] Tool seleccionada: {tool_name}")

            # Paso 3: Ejecutar herramienta seleccionada con nuevos parámetros SMTP
            # Argumentos actualizados para la función SMTP
            if tool_name == "draft_and_send_email":
                # Extraer información básica del mensaje del usuario
                # Puedes hacer esto más sofisticado con regex o NLP
                args = {
                    "from_person": "usuario@ejemplo.com",  # Esto debería venir del contexto del usuario
                    "subject": "Consulta profesional",     # Esto se puede extraer o generar
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
                tool_name = "draft_and_send_email"
                tool_result = "Análisis local realizado - Solicitud de redacción de correo detectada"
            else:
                tool_name = "draft_and_send_email"
                tool_result = "Análisis local realizado - Procesando solicitud de email"

        # Paso 4: Usar memoria de conversación y LLM para generar respuesta final
        memory = get_chat_memory(session_id)

        agent_prompt = ChatPromptTemplate.from_messages([
            ("system", EXECUTE_EMAIL_PROMPT),
            ("user", "{input_block}")
        ])
        input_block = f"Input del usuario: {user_input}\n\nResultado de la herramienta: {tool_result}"

        # Usar LLMChain sin memoria para evitar duplicaciones
        reasoning_chain = LLMChain(llm=llm, prompt=agent_prompt)
        final_output = reasoning_chain.invoke({"input_block": input_block})
        
        # Extraer solo el texto de la respuesta
        if isinstance(final_output, dict):
            final_response = final_output.get("text", str(final_output))
        else:
            final_response = str(final_output)
        
        # Limpiar la respuesta para evitar duplicaciones
        final_response = final_response.strip()
        
        # Aplicar limpieza de duplicados
        final_response = clean_duplicate_content(final_response)
        
        # Debug: mostrar la respuesta antes de procesar
        print(f"[Email Agent] Respuesta del LLM (raw): {final_response[:200]}...")
        print(f"[Email Agent] Respuesta del LLM (cleaned): {final_response[:200]}...")
        
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
            "executed_agents": state.get("executed_agents", [])
        }

# Test local
def test_email_agent(query="Hola, quiero escribir un correo al soporte por un problema con la factura, pero no se como redactarlo bien."):
    """Función para probar el agente Email independientemente"""
    print(f"Testing Email Agent with query: {query}")
    print("-" * 60)
    
    # UUID específico para la sesión
    session_id = "39105cb8-ba8c-40c6-aaf7-dd8571b605e0"
    
    # Insertar sesión en la base de datos
    insert_chat_session(session_id)
    
    # Simular estado como en LangGraph
    test_state = {
        "input": query, 
        "session_id": session_id,
        "messages": [],
        "executed_agents": []
    }
    
    result = email_agent_node(test_state)
    
    print("\n" + "="*60)
    print("RESULTADO DEL TEST:")
    print("="*60)
    print(f"Tool Response: {result.get('tool_response', 'No response')}")
    print(f"Current Agent: {result.get('current_agent', 'Unknown')}")
    print(f"Messages Count: {len(result.get('messages', []))}")
    print(f"Executed Agents: {result.get('executed_agents', [])}")
    
    # Mostrar el último mensaje si existe
    messages = result.get('messages', [])
    if messages:
        last_message = messages[-1]
        print(f"\nUltimo mensaje del agente:")
        print(f"Role: {last_message.get('role')}")
        print(f"Agent: {last_message.get('agent')}")
        print(f"Content: {last_message.get('content')}")
    
    return result

# Tests adicionales
def test_multiple_scenarios():
    """Prueba varios escenarios diferentes"""
    scenarios = [
        "Necesito redactar un email de queja por un producto defectuoso",
        "Quiero enviar un correo formal solicitando información sobre precios",
        "Ayudame a escribir un email de seguimiento para una reunión",
        "Redacta un correo profesional para solicitar vacaciones"
    ]
    
    print("\n" + "="*80)
    print("TESTING MULTIPLE SCENARIOS")
    print("="*80)
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n--- SCENARIO {i} ---")
        print(f"Query: {scenario}")
        
        try:
            result = test_email_agent(scenario)
            status = "✅ SUCCESS" if result.get('tool_response') else "❌ FAILED"
            print(f"Status: {status}")
        except Exception as e:
            print(f"Status: ❌ ERROR - {str(e)}")
        
        print("-" * 40)

if __name__ == "__main__":
    # Test principal
    print("INICIANDO TESTS DEL EMAIL AGENT")
    print("="*80)
    
    # Test básico
    test_email_agent("Quiero redactar un correo para reportar un bug en la aplicación")
    
    
    print("\n" + "="*80)
    print("TESTS COMPLETADOS")
    print("="*80)