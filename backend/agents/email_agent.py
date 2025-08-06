from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import os
import asyncio
import nest_asyncio
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.sse import sse_client

nest_asyncio.apply()
load_dotenv()

MCP_SERVER_URL = os.getenv("MCP_EMAIL_SERVER_URL", "http://localhost:8070")
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
{user_input}
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

def get_tool_selection_chain():
    prompt = PromptTemplate.from_template(SELECT_TOOL_PROMPT)
    return prompt | llm

def email_agent_node(state):
    try:
        user_input = state.get("input", "")
        messages = state.get("messages", [])
        executed_agents = state.get("executed_agents", [])
        
        if not user_input:
            return {"tool_response": "Error: No se recibió input del usuario."}

        print(f"[Email Agent] Procesando: {user_input}")
        print(f"[Email Agent] Agentes ejecutados previamente: {executed_agents}")

        tools = asyncio.run(get_available_tools())
        tools_str = "\n".join([f"{t['name']}: {t['description']}" for t in tools])
        selector = get_tool_selection_chain()
        decision_raw = selector.invoke({"tools": tools_str, "user_input": user_input})
        decision = decision_raw.content.strip()

        print(f"[Email Agent] Selector dijo: {decision}")

        tool_name = None
        for line in decision.splitlines():
            if "Action:" in line:
                tool_name = line.split("Action:")[1].strip()
                break

        if not tool_name:
            return {"tool_response": "Error: no se pudo determinar la herramienta a usar."}

        print(f"[Email Agent] Tool seleccionada: {tool_name}")

        # Argumentos mínimos
        if tool_name == "draft_professional_email":
            args = {
                "to": "soporte@empresa.com",  # o extraer de alguna UI
                "subject": "Consulta sobre el producto",
                "body": user_input
            }
        else:
            args = {"text": user_input}

        result = asyncio.run(execute_tool(tool_name, args))
        print(f"[Email Agent] Resultado: {result}")
        
        # Agregar respuesta al historial de mensajes
        messages.append({
            "role": "agent",
            "agent": "email_agent",
            "content": result,
            "timestamp": "email_response"
        })
        
        return {
            "tool_response": result,
            "current_agent": "email_agent",
            "messages": messages,
            "executed_agents": executed_agents
        }

    except Exception as e:
        print(f"Error en email_agent_node: {e}")
        error_msg = f"Error: {str(e)}"
        
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
    print(f"Test: {query}")
    test_state = {"input": query}
    result = email_agent_node(test_state)
    print(result)
    return result

if __name__ == "__main__":
    test_email_agent("Este es un resumen de tres correos donde se discute el contrato. El primero fue enviado el lunes con detalles legales. El segundo contiene propuestas de fechas. El tercero, una confirmación.")
    test_email_agent("Necesito mandar un correo al equipo de soporte diciendo que no puedo acceder a la plataforma desde ayer.")
