from langgraph.graph import StateGraph, END
from backend.utils.db_logger import save_message
# LangGraph espera un dict como estado
# Nosotros vamos a usar estas keys
# - input: texto del usuario
# - next_agent: string del nombre del agente que debe manejar el input
# - tool_response: resultado que devuelve la tool que el agente use
# - final_output: respuesta final del sistema

# Definimos el tipo del estado compartido
state = {
    "input": (str,),
    "next_agent": (str,),
    "tool_response": (str,),
    "final_output": (str,),
    "session_id": (str,)
}

# Nodo de clasificación con Gemini
from backend.supervisor.routing_llm import classify_with_gemini

def classify_intent(state):
    user_input = state["input"]
    agent = classify_with_gemini(user_input)
    return {"next_agent": agent}

#Nodos para logeo de mensajes
def log_user_message_node(state):
    try:
        save_message(state["session_id"], "user", state["input"])
    except Exception as e:
        print("[LogUser Error]", e)
    return {}  # No modifica el estado

def log_agent_response_node(state):
    try:
        save_message(state["session_id"], "agent", state["tool_response"])
    except Exception as e:
        print("[LogAgent Error]", e)
    return {}

# Nodo de finalización
# Guarda la respuesta final del agente
# (antes de pasarlo opcionalmente por Guardrails)
def finalize_output(state):
    return {
        "final_output": state.get("tool_response", "[Sin respuesta]")
    }

# Importar los agentes
from backend.agents.rag_agent import rag_agent_node
from backend.agents.sentiment_agent import sentiment_agent_node
from backend.agents.email_agent import email_agent_node
from backend.agents.tech_agent import tech_agent_node

# Construcción del grafo
builder = StateGraph(state)

# Agregar nodos
builder.add_node("classify", classify_intent)
builder.add_node("rag_agent", rag_agent_node)
builder.add_node("sentiment_agent", sentiment_agent_node)
builder.add_node("email_agent", email_agent_node)
builder.add_node("tech_agent", tech_agent_node)
builder.add_node("finalize", finalize_output)

# Flujo del grafo
builder.set_entry_point("log_user_message")
builder.add_edge("log_user_message", "classify")

builder.add_conditional_edges(
    "classify",
    # El valor de retorno de classify_intent es el nombre del nodo a ejecutar
    {
        "rag_agent": "rag_agent",
        "sentiment_agent": "sentiment_agent",
        "email_agent": "email_agent",
        "tech_agent": "tech_agent"
    }
)

# Cada agente devuelve el resultado en "tool_response"
# Después se pasa a finalize
builder.add_edge("rag_agent", "log_agent_response")
builder.add_edge("sentiment_agent", "log_agent_response")
builder.add_edge("email_agent", "log_agent_response")
builder.add_edge("tech_agent", "log_agent_response")

builder.add_edge("log_agent_response", "finalize")


# Nodo final del grafo
builder.set_finish_point("finalize")

# Compilar grafo
app = builder.compile()
