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

MCP_SERVER_URL = os.getenv("MCP_RAG_SERVER_URL")
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
{user_input}
"""


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
def get_tool_selection_chain():
    prompt = PromptTemplate.from_template(SELECT_TOOL_PROMPT)
    return prompt | llm

# Nodo principal para LangGraph o uso directo
def sentiment_agent_node(state):
    try:
        user_input = state.get("input", "")
        if not user_input:
            return {"tool_response": "Error: No se recibió input del usuario."}

        print(f"[Sentiment Agent] Procesando: {user_input}")

        tools = asyncio.run(get_available_tools())
        tools_str = "\n".join([f"{t['name']}: {t['description']}" for t in tools])
        selector = get_tool_selection_chain()
        decision_raw = selector.invoke({"tools": tools_str, "user_input": user_input})
        decision = decision_raw.content.strip()

        print(f"[Sentiment Agent] Respuesta del selector: {decision}")

        # Extraer nombre de herramienta del output
        tool_name = None
        for line in decision.splitlines():
            if "Action:" in line:
                tool_name = line.split("Action:")[1].strip()
                break

        if not tool_name:
            return {"tool_response": "Error: no se pudo determinar la herramienta a usar."}
        
        print(f"[Sentiment Agent] Tool seleccionada: {tool_name}")

        result = asyncio.run(execute_tool(tool_name, {"text": user_input}))
        print(f"[Sentiment Agent] Resultado: {result}")
        return {"tool_response": result}

    except Exception as e:
        print(f"Error en sentiment_agent_node: {e}")
        return {"tool_response": f"Error: {str(e)}"}

# Test local
def test_sentiment_agent(query="Esto es una mierda, no pienso usar mas esta app."):
    print(f"Test: {query}")
    test_state = {"input": query}
    result = sentiment_agent_node(test_state)
    print(result)
    return result

if __name__ == "__main__":
    test_sentiment_agent("Esta app es lo peor que vi, un asco, nunca responden.")
    test_sentiment_agent("Estoy un poco molesto con el tiempo de espera.")
    test_sentiment_agent("Nunca me responden nada de lo que hago, esto está muy mal.")
