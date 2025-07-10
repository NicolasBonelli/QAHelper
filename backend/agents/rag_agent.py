from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_community.tools.mcp import MCPToolkit
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv
from backend.config import DB_URL

load_dotenv()

MODEL= os.getenv("MODEL")
# LLM planner
llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0)

# MCP server donde está la tool de RAG expuesta (por ejemplo, /query_docs)
MCP_SERVER_URL = os.getenv("MCP_RAG_SERVER_URL")

# Toolkit que obtiene automáticamente todas las tools del servidor MCP
toolkit = MCPToolkit.from_url(MCP_SERVER_URL)


def get_rag_executor_with_memory(session_id: str) -> AgentExecutor:
    history = PostgresChatMessageHistory(
        session_id=session_id,
        connection_string=DB_URL,
        table_name="chat_messages"
    )

    memory = ConversationBufferMemory(
        chat_memory=history,
        return_messages=True
    )

    agent_with_memory = create_tool_calling_agent(llm=llm, tools=toolkit.get_tools())
    
    return AgentExecutor(agent=agent_with_memory, tools=toolkit.get_tools(), memory=memory, verbose=True)


def rag_agent_node(state: dict) -> dict:
    """
    Nodo de LangGraph para el agente RAG. Usa LangChain Agent + MCP Toolkit.
    Recupera el historial de la sesión desde PostgreSQL.
    """
    user_input = state["input"]
    session_id = state.get("session_id")  # Asegurate de incluir esto en el estado que pasás

    if not session_id:
        print("[RAG Agent Warning] session_id no encontrado en el estado.")
        return {"tool_response": "[Falta session_id]"}

    try:
        executor = get_rag_executor_with_memory(session_id)
        result = executor.invoke({"input": user_input})
        return {"tool_response": result["output"]}
    except Exception as e:
        print("[RAG Agent Error]", e)
        return {"tool_response": "[Error en RAG Agent]"}

