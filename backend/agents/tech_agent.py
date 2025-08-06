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

# Fix: Use the correct MCP server URL for tech server
MCP_SERVER_URL = os.getenv("MCP_TECH_SERVER_URL", "http://localhost:8060")
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
{user_input}
"""

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
def get_tool_selection_chain():
    prompt = PromptTemplate.from_template(SELECT_TOOL_PROMPT)
    return prompt | llm

# Nodo principal
def tech_agent_node(state):
    try:
        user_input = state.get("input", "")
        messages = state.get("messages", [])
        executed_agents = state.get("executed_agents", [])
        
        if not user_input:
            return {"tool_response": "Error: No se recibió input del usuario."}

        print(f"[Tech Agent] Procesando: {user_input}")
        print(f"[Tech Agent] Agentes ejecutados previamente: {executed_agents}")

        # Use asyncio.run() only if not already in an async context
        try:
            loop = asyncio.get_running_loop()
            # If we're in an async context, create a new task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                tools = executor.submit(asyncio.run, get_available_tools()).result()
        except RuntimeError:
            # No running loop, safe to use asyncio.run()
            tools = asyncio.run(get_available_tools())

        tools_str = "\n".join([f"{t['name']}: {t['description']}" for t in tools])
        selector = get_tool_selection_chain()
        decision_raw = selector.invoke({"tools": tools_str, "user_input": user_input})
        decision = decision_raw.content.strip()

        print(f"[Tech Agent] Respuesta del selector: {decision}")

        # Extraer nombre de herramienta del output
        tool_name = None
        for line in decision.splitlines():
            if "Action:" in line:
                tool_name = line.split("Action:")[1].strip()
                break

        if not tool_name:
            return {"tool_response": "Error: no se pudo determinar la herramienta a usar."}
        
        print(f"[Tech Agent] Tool seleccionada: {tool_name}")

        argument_key = "tabla" if tool_name == "generate_excel_from_data" else "text"
        
        # Use asyncio.run() only if not already in an async context
        try:
            loop = asyncio.get_running_loop()
            # If we're in an async context, create a new task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                result = executor.submit(asyncio.run, execute_tool(tool_name, {argument_key: user_input})).result()
        except RuntimeError:
            # No running loop, safe to use asyncio.run()
            result = asyncio.run(execute_tool(tool_name, {argument_key: user_input}))

        print(f"[Tech Agent] Resultado: {result}")
        
        # Agregar respuesta al historial de mensajes
        messages.append({
            "role": "agent",
            "agent": "tech_agent",
            "content": result,
            "timestamp": "tech_response"
        })
        
        return {
            "tool_response": result,
            "current_agent": "tech_agent",
            "messages": messages,
            "executed_agents": executed_agents
        }

    except Exception as e:
        print(f"Error en tech_agent_node: {e}")
        error_msg = f"Error: {str(e)}"
        
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
    print(f"Test: {query}")
    test_state = {"input": query}
    result = tech_agent_node(test_state)
    print(result)
    return result

if __name__ == "__main__":
    test_tech_agent("nombre,edad\nLucia,25\nPedro,33")
    test_tech_agent("Este es un articulo largo sobre la importancia de la IA en la educación moderna. La IA permite personalizar el aprendizaje y mejorar los resultados educativos. Sin embargo, también plantea desafíos éticos que deben ser abordados...")
